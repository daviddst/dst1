# Emplacement exact : /volume/dst1-web/server.py
# (remplace le fichier existant)

import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from livekit import api

app = FastAPI(title="DST1 Web")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LIVEKIT_API_KEY = os.environ["LIVEKIT_API_KEY"]
LIVEKIT_API_SECRET = os.environ["LIVEKIT_API_SECRET"]
LIVEKIT_URL = os.environ["LIVEKIT_URL"]

# URL interne (reseau Docker dst1-network) du serveur texte expose par
# dst1-agent. Jamais accessible depuis l'exterieur directement : seul
# dst1-web fait relais, en tant que facade HTTP unique du systeme.
DST1_AGENT_TEXT_URL = os.environ.get("DST1_AGENT_TEXT_URL", "http://dst1-agent:8090")

LOG_FILE_PATH = "/app/logs/agent.log"

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/config")
def config():
    return {"livekit_url": LIVEKIT_URL}


@app.get("/token")
def get_token(identity: str = "utilisateur-lan", room: str = "dst1-main"):
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(api.VideoGrants(room_join=True, room=room))
    )
    return {"token": token.to_jwt(), "url": LIVEKIT_URL}


@app.post("/text-query")
async def text_query_proxy(payload: dict):
    """Relais vers le serveur texte interne de dst1-agent. Permet a n8n
    (WA Main Router, workflow de test) de 'chatter' avec DST1 en texte,
    sans exposer directement le port interne 8090 de dst1-agent."""
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(f"{DST1_AGENT_TEXT_URL}/text-query", json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            return {"error": f"Echec de la requete vers dst1-agent : {e}"}


async def tail_log_file():
    import asyncio
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.rstrip()}\n\n"
                else:
                    await asyncio.sleep(0.5)
    except FileNotFoundError:
        yield f"data: [Fichier de log introuvable pour l'instant : {LOG_FILE_PATH}]\n\n"


@app.get("/logs/stream")
async def stream_logs():
    return StreamingResponse(tail_log_file(), media_type="text/event-stream")
