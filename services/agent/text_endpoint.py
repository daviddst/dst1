import os
import logging
import yaml
import asyncio
import time
from typing import Any
from collections import defaultdict

from fastapi import FastAPI
from pydantic import BaseModel
from google import genai

from tool_loader import discover_tools_from_n8n


logger = logging.getLogger("dst1-text-endpoint")
app = FastAPI(title="DST1 Text Query Endpoint")

AGENT_CONFIG_PATH = os.environ.get("AGENT_CONFIG_PATH", "agent_config.yaml")

# Memoire RAM reservee a /text-query.
# Elle n'est pas utilisee par le flux LiveKit.
CONVERSATION_MEMORY: dict[str, dict[str, Any]] = {}

# Protege une session contre deux messages traites simultanement.
CONVERSATION_LOCKS: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# Nombre indicatif de tours conserves.
MAX_CONVERSATION_TURNS = int(
    os.environ.get("DST1_TEXT_MEMORY_MAX_TURNS", "12")
)

# Retention des sessions en RAM : une heure par defaut.
CONVERSATION_TTL_SECONDS = int(
    os.environ.get("DST1_TEXT_MEMORY_TTL_SECONDS", "3600")
)


class TextQuery(BaseModel):
    message: str
    session_id: str | None = None


def _load_agent_config():
    with open(AGENT_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _clean_schema_for_gemini(schema: dict) -> dict:
    """
    Retire les elements JSON Schema non acceptes par l'API Gemini native.
    """
    if not isinstance(schema, dict):
        return schema

    cleaned = {
        key: value
        for key, value in schema.items()
        if key not in ("additionalProperties", "additional_properties")
    }

    if "properties" in cleaned and isinstance(cleaned["properties"], dict):
        cleaned["properties"] = {
            property_name: _clean_schema_for_gemini(property_schema)
            for property_name, property_schema in cleaned["properties"].items()
        }

    if "items" in cleaned and isinstance(cleaned["items"], dict):
        cleaned["items"] = _clean_schema_for_gemini(cleaned["items"])

    return cleaned


def _get_session_id(query: TextQuery) -> str:
    """
    Sans session_id, conserve la compatibilite avec query_dst1.sh.
    """
    session_id = str(query.session_id or "").strip()

    if not session_id:
        return "text:default"

    return session_id[:512]


def _prune_conversation_memory() -> None:
    """
    Supprime les sessions RAM expirees.
    """
    now = time.time()

    expired_session_ids = [
        session_id
        for session_id, session in CONVERSATION_MEMORY.items()
        if now - float(session.get("updated_at", 0))
        > CONVERSATION_TTL_SECONDS
    ]

    for session_id in expired_session_ids:
        CONVERSATION_MEMORY.pop(session_id, None)
        CONVERSATION_LOCKS.pop(session_id, None)

    if expired_session_ids:
        logger.info(
            "Memoire texte purgeee : %s session(s) expiree(s).",
            len(expired_session_ids),
        )


def _part_has_function_call(part: Any) -> bool:
    """
    Detecte un function_call dans un Part Gemini.
    """
    return bool(getattr(part, "function_call", None))


def _part_has_function_response(part: Any) -> bool:
    """
    Detecte un function_response dans un Part Gemini.
    """
    return bool(getattr(part, "function_response", None))


def _content_has_function_call(content: Any) -> bool:
    """
    Retourne True si un contenu Gemini contient un ou plusieurs function_call.
    """
    parts = getattr(content, "parts", None) or []

    return any(_part_has_function_call(part) for part in parts)


def _content_has_function_response(content: Any) -> bool:
    """
    Retourne True si un contenu Gemini contient un ou plusieurs
    function_response.
    """
    parts = getattr(content, "parts", None) or []

    return any(_part_has_function_response(part) for part in parts)


def _sanitize_history(contents: list[Any]) -> list[Any]:
    """
    Nettoie l'historique avant envoi a Gemini.

    Regle Gemini :
      function_response doit arriver immediatement apres le content model
      qui contient le function_call correspondant.

    Une ancienne version de la memoire pouvait tronquer la liste au milieu
    de ce couple. Cette fonction elimine tout historique invalide :
    - une function_response orpheline ;
    - un function_call sans function_response immediatement derriere ;
    - les contenus avant le dernier point coherent.

    Les appels tools futurs conserveront toujours :
      model(function_call) -> user(function_response)
    """
    if not contents:
        return []

    clean: list[Any] = []
    index = 0

    while index < len(contents):
        current = contents[index]

        if _content_has_function_response(current):
            # Une function_response ne peut jamais etre le premier element
            # d'un historique ou suivre autre chose qu'un function_call.
            logger.warning(
                "Historique Gemini invalide : function_response orpheline ignoree."
            )
            index += 1
            continue

        if _content_has_function_call(current):
            # Il faut obligatoirement trouver la function_response juste apres.
            if (
                index + 1 < len(contents)
                and _content_has_function_response(contents[index + 1])
            ):
                clean.append(current)
                clean.append(contents[index + 1])
                index += 2
                continue

            logger.warning(
                "Historique Gemini invalide : function_call sans "
                "function_response immediate ignore."
            )
            index += 1
            continue

        clean.append(current)
        index += 1

    # Protection de taille : on retire des blocs coherents depuis le debut.
    max_items = max(MAX_CONVERSATION_TURNS * 3, 18)

    while len(clean) > max_items:
        first = clean.pop(0)

        # Si on retire un function_call, retirer egalement sa reponse.
        if _content_has_function_call(first):
            if clean and _content_has_function_response(clean[0]):
                clean.pop(0)

    # Apres coupe, une function_response ne doit jamais etre le premier item.
    while clean and _content_has_function_response(clean[0]):
        clean.pop(0)

    # Si le dernier element est un function_call seul, le retirer.
    if clean and _content_has_function_call(clean[-1]):
        clean.pop()

    return clean


def _format_error_response(
    query: TextQuery,
    session_id: str,
    tools_by_name: dict,
    actions_effectuees: list,
    message: str,
) -> dict:
    """
    Retour standardise pour que n8n puisse afficher une erreur WhatsApp.
    """
    return {
        "success": False,
        "error": message,
        "message_utilisateur": query.message,
        "session_id": session_id,
        "outils_disponibles": list(tools_by_name.keys()),
        "actions_effectuees": actions_effectuees,
        "reponse_texte": (
            "Je n'ai pas pu traiter cette demande a cause d'un probleme "
            "technique. Reessaie dans quelques instants."
        ),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "memory_sessions": len(CONVERSATION_MEMORY),
    }


@app.post("/text-query")
async def text_query(query: TextQuery):
    """
    Endpoint texte a memoire courte, independant de LiveKit.

    Exemple :
      User : Active les reponses automatiques
      DST1 : Pour quel contact ?
      User : Sarah
      DST1 : recherche Sarah puis poursuit l'action.
    """
    _prune_conversation_memory()

    session_id = _get_session_id(query)
    lock = CONVERSATION_LOCKS[session_id]

    async with lock:
        try:
            tools = await discover_tools_from_n8n()
        except Exception as exc:
            logger.exception("Echec decouverte des outils : %s", exc)

            return {
                "success": False,
                "error": f"Impossible de decouvrir les outils n8n : {exc}",
                "message_utilisateur": query.message,
                "session_id": session_id,
                "outils_disponibles": [],
                "actions_effectuees": [],
                "reponse_texte": (
                    "Je ne peux pas acceder a mes outils pour le moment. "
                    "Reessaie dans quelques instants."
                ),
            }

        config = _load_agent_config()
        instructions = config["agent"]["instructions"]

        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

        function_declarations = []
        tools_by_name = {}

        for tool in tools:
            info = getattr(tool, "info", None)
            raw_schema = getattr(info, "raw_schema", None) or {}

            name = raw_schema.get("name")
            if not name:
                continue

            cleaned_parameters = _clean_schema_for_gemini(
                raw_schema.get(
                    "parameters",
                    {
                        "type": "object",
                        "properties": {},
                    },
                )
            )

            function_declarations.append({
                "name": name,
                "description": raw_schema.get("description", ""),
                "parameters": cleaned_parameters,
            })

            tools_by_name[name] = tool

        model_name = config["llm"].get(
            "text_model",
            "gemini-3.5-flash-lite",
        )

        existing_session = CONVERSATION_MEMORY.get(session_id)

        if existing_session and existing_session.get("contents"):
            old_contents = list(existing_session["contents"])
            contents = _sanitize_history(old_contents)

            # Si l'historique est devenu totalement vide apres nettoyage,
            # on repart sur une nouvelle conversation propre.
            if contents:
                contents.append({
                    "role": "user",
                    "parts": [
                        {
                            "text": query.message,
                        }
                    ],
                })

                logger.info(
                    "Reprise conversation session=%s | historique nettoye=%s element(s)",
                    session_id,
                    len(contents),
                )
            else:
                logger.warning(
                    "Historique session=%s invalide ou vide apres nettoyage. "
                    "Nouvelle conversation.",
                    session_id,
                )

        else:
            contents = []

        if not contents:
            contents = [{
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"{instructions}\n\n"
                            "Tu conserves le contexte de cette conversation. "
                            "Si un parametre obligatoire manque avant l'appel "
                            "d'un outil, pose une question courte et precise. "
                            "Quand l'utilisateur repond ensuite, utilise sa "
                            "reponse pour poursuivre l'action precedente sans "
                            "lui demander de tout reformuler.\n\n"
                            f"Demande de l'utilisateur : {query.message}"
                        ),
                    }
                ],
            }]

            logger.info(
                "Nouvelle conversation session=%s",
                session_id,
            )

        actions_effectuees = []
        texte_final = ""
        max_tours = 5

        try:
            for _ in range(max_tours):
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config={
                        "tools": [
                            {
                                "function_declarations": function_declarations,
                            }
                        ]
                    } if function_declarations else None,
                )

                if not response.candidates:
                    texte_final = (
                        "Je n'ai pas pu generer de reponse. "
                        "Reessaie dans quelques instants."
                    )
                    break

                candidate = response.candidates[0]

                if not candidate.content or not candidate.content.parts:
                    texte_final = (
                        "Je n'ai pas pu generer de reponse exploitable. "
                        "Reessaie dans quelques instants."
                    )
                    break

                has_function_call = False
                function_response_parts = []
                candidate_text = ""

                for part in candidate.content.parts:
                    if _part_has_function_call(part):
                        has_function_call = True

                        function_name = part.function_call.name
                        function_args = dict(part.function_call.args)
                        tool = tools_by_name.get(function_name)

                        logger.info(
                            "Text-query tool call -> %s | session=%s | args=%s",
                            function_name,
                            session_id,
                            function_args,
                        )

                        if tool is None:
                            result = {
                                "success": False,
                                "error": f"Outil inconnu : {function_name}",
                            }
                        else:
                            handler = (
                                tool.__wrapped__
                                if hasattr(tool, "__wrapped__")
                                else tool
                            )

                            try:
                                result = await handler(function_args, None)
                            except Exception as exc:
                                logger.exception(
                                    "Erreur execution tool %s : %s",
                                    function_name,
                                    exc,
                                )

                                result = {
                                    "success": False,
                                    "error": (
                                        f"Erreur pendant l'execution de "
                                        f"l'outil {function_name} : {exc}"
                                    ),
                                }

                        actions_effectuees.append({
                            "outil": function_name,
                            "arguments": function_args,
                            "resultat": result,
                        })

                        function_response_parts.append({
                            "function_response": {
                                "name": function_name,
                                "response": {
                                    "result": result,
                                },
                            }
                        })

                    elif getattr(part, "text", None):
                        candidate_text += part.text

                # Conserver le contenu original est necessaire pour conserver
                # le thought_signature Gemini.
                contents.append(candidate.content)

                if has_function_call:
                    # Gemini exige cette reponse immediatement apres
                    # candidate.content contenant function_call.
                    contents.append({
                        "role": "user",
                        "parts": function_response_parts,
                    })
                else:
                    texte_final += candidate_text
                    break

        except Exception as exc:
            logger.exception(
                "Erreur Gemini session=%s : %s",
                session_id,
                exc,
            )

            # Ne pas conserver l'historique ayant provoque l'erreur.
            # On garde uniquement une conversation nettoyee, afin que la
            # prochaine demande puisse repartir correctement.
            safe_contents = _sanitize_history(contents)

            CONVERSATION_MEMORY[session_id] = {
                "contents": safe_contents,
                "updated_at": time.time(),
            }

            return _format_error_response(
                query=query,
                session_id=session_id,
                tools_by_name=tools_by_name,
                actions_effectuees=actions_effectuees,
                message=f"Erreur Gemini : {exc}",
            )

        # Sauvegarde un historique toujours nettoye et structurellement valide.
        contents = _sanitize_history(contents)

        CONVERSATION_MEMORY[session_id] = {
            "contents": contents,
            "updated_at": time.time(),
        }

        return {
            "success": True,
            "message_utilisateur": query.message,
            "session_id": session_id,
            "outils_disponibles": list(tools_by_name.keys()),
            "actions_effectuees": actions_effectuees,
            "reponse_texte": (
                texte_final.strip()
                or "Action(s) effectuee(s), voir actions_effectuees."
            ),
        }
