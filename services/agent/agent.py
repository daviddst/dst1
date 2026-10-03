# Emplacement exact : /volume/dst1-agent/agent.py
# (remplace le fichier existant — apres modification : docker compose restart dst1-agent)
# Ajout : demarrage en parallele d'un petit serveur FastAPI interne (port
# 8090, jamais expose publiquement) permettant de tester/chatter avec DST1
# en texte, via dst1-web qui fait relais (/text-query).

import os
import asyncio
import threading
import logging
import logging.handlers
import yaml
import uvicorn
from dotenv import load_dotenv
from livekit.agents import (
    JobContext,
    JobProcess,
    Agent,
    AgentSession,
    AgentServer,
    cli,
    room_io,
    ErrorEvent,
)
from livekit.plugins import silero, google
from tool_loader import discover_tools_from_n8n, build_tools_summary
from text_endpoint import app as text_app
from diagnostic_tool import run_diagnostic_on_error

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dst1-agent")

try:
    file_handler = logging.handlers.RotatingFileHandler(
        "/app/logs/agent.log", maxBytes=5_000_000, backupCount=2, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logging.getLogger().addHandler(file_handler)
except FileNotFoundError:
    logger.warning("Dossier /app/logs introuvable : logs non partages avec dst1-web.")

AGENT_CONFIG_PATH = os.environ.get("AGENT_CONFIG_PATH", "agent_config.yaml")

MAX_LLM_RETRIES = 3
RETRY_BACKOFF_SECONDS = [2, 5, 10]

MESSAGE_RECUPERATION_ERREUR = (
    "Désolé, j'ai eu un petit souci technique momentané. "
    "Peux-tu répéter ta dernière question ?"
)

server = AgentServer()


def load_agent_config(path: str = AGENT_CONFIG_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if not config or "agent" not in config or "llm" not in config:
            raise ValueError("agent_config.yaml incomplet : sections 'agent' et 'llm' requises")
        return config
    except FileNotFoundError:
        logger.error(f"Fichier de config introuvable : {path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Erreur de parsing YAML dans {path}: {e}")
        raise


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load(
        min_speech_duration=0.3,
        min_silence_duration=0.8,
    )
    proc.userdata["agent_config"] = load_agent_config()
    logger.info(f"Config agent chargee : {proc.userdata['agent_config']['agent']['name']}")

    try:
        proc.userdata["tools"] = asyncio.run(discover_tools_from_n8n())
    except Exception as e:
        logger.error(f"Echec de la decouverte automatique des outils via n8n : {e}")
        proc.userdata["tools"] = []


server.setup_fnc = prewarm


class DST1Assistant(Agent):
    def __init__(self, config: dict, tools) -> None:
        agent_cfg = config["agent"]
        base_instructions = agent_cfg["instructions"]
        tools_summary = build_tools_summary(tools)

        full_instructions = (
            f"{base_instructions}\n\n"
            f"{tools_summary}\n\n"
            "N'invente jamais une capacite qui ne figure pas dans cette liste : "
            "si l'utilisateur demande quelque chose hors de ces outils, dis-le "
            "clairement plutot que de pretendre pouvoir le faire."
        )

        super().__init__(instructions=full_instructions, tools=tools)


def build_realtime_model(llm_cfg: dict):
    return google.beta.realtime.RealtimeModel(
        model=llm_cfg["model"],
        voice=llm_cfg.get("voice", "Puck"),
        temperature=llm_cfg.get("temperature", 0.7),
        enable_affective_dialog=llm_cfg.get("enable_affective_dialog", False),
        proactivity=llm_cfg.get("proactivity", False),
    )


def register_error_handler(session: AgentSession):
    @session.on("error")
    def on_error(ev: ErrorEvent):
        source_name = type(ev.source).__name__
        logger.error(f"ErrorEvent recu sur {source_name} : {ev.error}")

        if ev.error.recoverable:
            return

        ev.error.recoverable = True
        logger.info(f"Erreur sur {source_name} marquee comme recuperable, session maintenue.")

        try:
            session.say(MESSAGE_RECUPERATION_ERREUR, allow_interruptions=False)
        except Exception as say_err:
            logger.error(f"Impossible de notifier l'utilisateur de l'erreur : {say_err}")

        # Lance un diagnostique asynchrone en arriere-plan via Thread
        def run_diagnostic_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    run_diagnostic_on_error(error_msg=f"{source_name}: {str(ev.error)}")
                )
                loop.close()
            except Exception as diag_err:
                logger.error(f"Erreur lors du lancement du diagnostique : {diag_err}")

        thread = threading.Thread(target=run_diagnostic_in_thread, daemon=True)
        thread.start()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    config = ctx.proc.userdata["agent_config"]
    tools = ctx.proc.userdata["tools"]
    llm_cfg = config["llm"]
    room_cfg = config.get("room", {})

    last_error = None

    for attempt in range(1, MAX_LLM_RETRIES + 1):
        try:
            session = AgentSession(
                llm=build_realtime_model(llm_cfg),
                vad=ctx.proc.userdata["vad"],
            )
            register_error_handler(session)

            await session.start(
                room=ctx.room,
                agent=DST1Assistant(config=config, tools=tools),
                room_options=room_io.RoomOptions(
                    video_input=room_cfg.get("video_input", True),
                ),
            )
            await ctx.connect()

            greeting = config["agent"].get("greeting")
            if greeting:
                await session.generate_reply(
                    instructions=f"Salue l'utilisateur avec exactement ce message : {greeting}"
                )
            else:
                await session.generate_reply()

            return

        except Exception as e:
            last_error = e
            logger.error(f"Tentative {attempt}/{MAX_LLM_RETRIES} de demarrage de session a echoue : {e}")

            if attempt < MAX_LLM_RETRIES:
                delay = RETRY_BACKOFF_SECONDS[min(attempt - 1, len(RETRY_BACKOFF_SECONDS) - 1)]
                logger.info(f"Nouvelle tentative dans {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Echec definitif apres {MAX_LLM_RETRIES} tentatives. Derniere erreur : {last_error}")
                raise


def run_text_endpoint():
    """Lance le serveur texte interne (port 8090) dans un thread separe,
    en parallele du worker LiveKit. Jamais expose publiquement : seul
    dst1-web (relais /text-query) y accede via le reseau Docker interne."""
    uvicorn.run(text_app, host="0.0.0.0", port=8090, log_level="info")


if __name__ == "__main__":
    threading.Thread(target=run_text_endpoint, daemon=True).start()
    cli.run_app(server)
