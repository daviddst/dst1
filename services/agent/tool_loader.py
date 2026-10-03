# Emplacement exact : /volume/dst1-agent/tool_loader.py
# (remplace le fichier existant — apres modification : docker compose restart dst1-agent, pas de rebuild)
#
# Historique des correctifs integres dans cette version :
#  1. Association Webhook <-> ToolSchema via parcours du graphe de
#     connexions (necessaire quand plusieurs paires Webhook+ToolSchema
#     coexistent dans un meme workflow).
#  2. Recherche de noeud ToolSchema par prefixe ("ToolSchema*"), pas par
#     egalite stricte (ToolSchema2, ToolSchema3, etc.).
#  3. Migration vers httpx.AsyncClient (async) pour eviter de bloquer la
#     boucle asyncio de l'agent pendant les appels reseau vers n8n.
#  4. Gestion de la PAGINATION de l'API n8n GET /workflows (nextCursor) :
#     sans cela, certains workflows tagues dst1-tool pouvaient etre omis
#     silencieusement des lors que le nombre total de workflows depassait
#     la taille d'une page. Le filtrage par tag est desormais fait cote
#     Python, sur la liste complete paginee, plutot que via le parametre
#     ?tags= de l'API (comportement peu fiable observe en pratique).

import os
import json
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional

import httpx
from livekit.agents import function_tool, RunContext

# Import du diagnostic tool interne
try:
    from diagnostic_tool import create_diagnostic_function_tool
    DIAGNOSTIC_TOOL_AVAILABLE = True
except ImportError:
    DIAGNOSTIC_TOOL_AVAILABLE = False
    create_diagnostic_function_tool = None

logger = logging.getLogger("dst1-tool-loader")

N8N_WEBHOOK_BASE = os.environ.get("N8N_WEBHOOK_BASE", "http://dst1-n8n:5678/webhook")
N8N_API_BASE = os.environ.get("N8N_API_BASE", "http://dst1-n8n:5678/api/v1")
N8N_API_KEY = os.environ.get("N8N_API_KEY")
TOOL_TAG = os.environ.get("DST1_TOOL_TAG", "dst1-tool")
N8N_TIMEOUT = int(os.environ.get("N8N_TOOL_TIMEOUT", "15"))

# Client HTTP asynchrone partage, reutilise entre tous les appels d'outils
# (evite de recreer une connexion TCP a chaque appel, et surtout evite de
# bloquer la boucle asyncio de l'agent pendant l'attente reseau).
_async_client: Optional[httpx.AsyncClient] = None


def _get_async_client() -> httpx.AsyncClient:
    """Return a shared async HTTP client (lazy init).

    The client is reused for discovery calls to avoid recreating TCP
    connections repeatedly.
    """
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(timeout=N8N_TIMEOUT)
    return _async_client


async def _call_n8n_webhook(webhook_path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Appelle un webhook n8n pour l'execution d'un tool.

    Un client HTTP dedie est volontairement cree pour chaque appel de tool :
    cela evite qu'une connexion keep-alive partagee avec les appels de
    decouverte n8n reste bloquee ou reutilise une socket devenue invalide.
    """
    url = f"{N8N_WEBHOOK_BASE}/{webhook_path}"

    timeout = httpx.Timeout(
        connect=5.0,
        read=float(N8N_TIMEOUT),
        write=10.0,
        pool=5.0,
    )

    logger.info(
        f"Appel n8n en cours -> {webhook_path} | "
        f"url={url} | payload={payload}"
    )

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            headers={"Connection": "close", "Accept": "application/json"},
        ) as client:
            resp = await client.post(url, json=payload)

        logger.info(
            f"Reponse n8n recue <- {webhook_path} | "
            f"status={resp.status_code} | body={resp.text[:2000]}"
        )

        resp.raise_for_status()

        try:
            result = resp.json()
        except ValueError:
            result = {"result": resp.text}

        logger.info(f"Resultat tool n8n <- {webhook_path} | result={result}")

        return result

    except httpx.TimeoutException as e:
        logger.error(
            f"Timeout appel n8n webhook '{webhook_path}' " f"apres {N8N_TIMEOUT}s : {e}"
        )
        return {"error": (f"Le workflow '{webhook_path}' n'a pas repondu " f"dans le delai imparti.")}

    except httpx.HTTPError as e:
        logger.error(
            f"Erreur appel n8n webhook '{webhook_path}' : " f"{type(e).__name__}: {e}"
        )
        return {"error": f"Le workflow '{webhook_path}' a echoue : {e}"}

    except Exception as e:
        logger.exception(
            f"Erreur inattendue pendant l'appel du workflow " f"'{webhook_path}' : {type(e).__name__}: {e}"
        )
        return {"error": (f"Erreur inattendue lors de l'appel du workflow " f"'{webhook_path}' : {e}")}

def _make_tool_handler(
    webhook_path: str,
) -> Callable[[Dict[str, Any], RunContext], Coroutine[Any, Any, Dict[str, Any]]]:
    """Create a dynamic async handler that forwards tool calls to n8n webhook.

    The returned handler signature matches what `function_tool` expects.
    """

    async def handler(raw_arguments: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        logger.info(f"Tool call -> {webhook_path} | args={raw_arguments}")
        return await _call_n8n_webhook(webhook_path, raw_arguments)

    return handler


def _next_node_names(connections: Dict[str, Any], node_name: str) -> List[str]:
    """Return downstream node names connected to `node_name` via the 'main' output."""
    outputs = connections.get(node_name, {}).get("main", [])
    names: List[str] = []
    for output in outputs:
        for conn in output:
            n = conn.get("node")
            if n:
                names.append(n)
    return names


def _find_downstream_toolschema(
    connections: Dict[str, Any],
    start_name: str,
    nodes_by_name: Dict[str, Any],
    max_depth: int = 6,
) -> Optional[Dict[str, Any]]:
    """Breadth-first search from `start_name` and return first node whose
    `name` starts with 'ToolSchema'. Returns None when not found within
    `max_depth` levels."""

    visited = set()
    queue: List[str] = [start_name]
    depth = 0

    while queue and depth <= max_depth:
        next_queue: List[str] = []
        for name in queue:
            if name in visited:
                continue
            visited.add(name)

            node = nodes_by_name.get(name)
            if node and node.get("name", "").startswith("ToolSchema"):
                return node

            next_queue.extend(_next_node_names(connections, name))
        queue = next_queue
        depth += 1

    return None


def _extract_tool_definitions(workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all tool definitions from a workflow by associating each
    Webhook node with a downstream ToolSchema* node via the connection graph.
    """
    nodes = workflow.get("nodes", [])
    connections = workflow.get("connections", {})
    wf_name = workflow.get("name", "?")

    nodes_by_name: Dict[str, Any] = {n.get("name"): n for n in nodes}
    webhook_nodes = [n for n in nodes if n.get("type") == "n8n-nodes-base.webhook"]

    tool_defs: List[Dict[str, Any]] = []

    for webhook_node in webhook_nodes:
        webhook_name = webhook_node.get("name")
        webhook_path = webhook_node.get("parameters", {}).get("path")

        if not webhook_path:
            logger.warning(
                f"Workflow '{wf_name}' : webhook '{webhook_name}' sans 'path' defini, ignore."
            )
            continue

        schema_node = _find_downstream_toolschema(connections, webhook_name, nodes_by_name)
        if not schema_node:
            logger.warning(
                f"Workflow '{wf_name}' : aucun noeud 'ToolSchema*' trouve en aval du webhook '{webhook_name}', ignore."
            )
            continue

        assignments = schema_node.get("parameters", {}).get("assignments", {}).get("assignments", [])
        values = {a.get("name"): a.get("value") for a in assignments}

        name = values.get("tool_name")
        description = values.get("tool_description")
        parameters_raw = values.get("tool_parameters")
        require_confirmation = str(values.get("require_confirmation", "false")).lower() == "true"

        if not name or not description or not parameters_raw:
            logger.warning(
                f"Workflow '{wf_name}' : ToolSchema incomplet pour le webhook '{webhook_name}', ignore."
            )
            continue

        try:
            parameters = json.loads(parameters_raw)
        except json.JSONDecodeError as e:
            logger.warning(
                f"Workflow '{wf_name}' : tool_parameters invalide pour '{name}' ({e}), ignore."
            )
            continue

        tool_defs.append({
            "name": name,
            "description": description,
            "webhook": webhook_path,
            "parameters": parameters,
            "require_confirmation": require_confirmation,
        })

    return tool_defs


async def _fetch_all_workflows(client: httpx.AsyncClient, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """Recupere TOUS les workflows via l'API n8n, en suivant la pagination
    (nextCursor). Sans cette gestion, l'API peut ne retourner qu'une seule
    page de resultats, omettant silencieusement des workflows tagues
    dst1-tool des que le nombre total de workflows depasse la taille
    d'une page."""
    all_workflows = []
    cursor = None

    while True:
        params = {"active": "true"}
        if cursor:
            params["cursor"] = cursor

        resp = await client.get(
            f"{N8N_API_BASE}/workflows", headers=headers, params=params, timeout=N8N_TIMEOUT
        )
        resp.raise_for_status()
        page = resp.json()

        all_workflows.extend(page.get("data", []))

        cursor = page.get("nextCursor")
        if not cursor:
            break

    return all_workflows


async def discover_tools_from_n8n() -> List[Any]:
    """Interroge l'API REST de n8n pour decouvrir automatiquement tous les
    outils definis dans les workflows tagues 'dst1-tool'. Un meme workflow
    peut contenir plusieurs outils (plusieurs paires Webhook + ToolSchema).

    Le filtrage par tag est effectue cote Python, sur la liste COMPLETE et
    PAGINEE des workflows, plutot que via le parametre ?tags= de l'API n8n
    (comportement peu fiable observe en pratique avec un grand nombre de
    workflows).

    Aucun fichier statique (tools.yaml) n'est requis : ajouter un outil =
    creer/tagger un workflow n8n avec la convention Webhook -> ToolSchema*,
    puis redemarrer l'agent."""
    if not N8N_API_KEY:
        raise RuntimeError(
            "N8N_API_KEY non defini dans l'environnement : impossible d'interroger "
            "l'API n8n pour la decouverte automatique des outils."
        )

    headers: Dict[str, str] = {"X-N8N-API-KEY": N8N_API_KEY}
    client = _get_async_client()

    all_workflows = await _fetch_all_workflows(client, headers)
    logger.info(
        f"{len(all_workflows)} workflow(s) recupere(s) au total depuis l'API n8n (toutes pages confondues)."
    )

    tools: List[Any] = []
    for wf_summary in all_workflows:
        tags = [t.get("name") for t in wf_summary.get("tags", []) or []]
        if TOOL_TAG not in tags:
            continue

        wf_id = wf_summary["id"]
        wf_resp = await client.get(
            f"{N8N_API_BASE}/workflows/{wf_id}", headers=headers, timeout=N8N_TIMEOUT
        )
        wf_resp.raise_for_status()
        workflow = wf_resp.json()

        tool_defs = _extract_tool_definitions(workflow)

        for tool_def in tool_defs:
            raw_schema = {
                "type": "function",
                "name": tool_def["name"],
                "description": tool_def["description"],
                "parameters": tool_def["parameters"],
            }
            handler = _make_tool_handler(tool_def["webhook"])
            tools.append(function_tool(handler, raw_schema=raw_schema))
            logger.info(
                f"Tool decouvert automatiquement : '{tool_def['name']}' "
                f"(workflow '{workflow.get('name')}', webhook '{tool_def['webhook']}')"
            )

    logger.info(
        f"{len(tools)} tool(s) decouvert(s) automatiquement via n8n (tag '{TOOL_TAG}')"
    )
    
    # Ajouter le tool diagnostic interne (non n8n)
    if DIAGNOSTIC_TOOL_AVAILABLE and create_diagnostic_function_tool:
        try:
            diagnostic_tool = create_diagnostic_function_tool()
            if diagnostic_tool:
                tools.append(diagnostic_tool)
                logger.info("Tool interne 'analyser_logs_diagnostic' (diagnostic) enregistré")
        except Exception as e:
            logger.warning(f"Erreur lors de l'enregistrement du diagnostic tool : {e}")
    
    return tools


def build_tools_summary(tools) -> str:
    """Construit un resume texte des outils disponibles, a injecter dans le
    prompt systeme de l'agent. Se met a jour automatiquement a chaque
    decouverte de tools via n8n, sans intervention manuelle."""
    if not tools:
        return "Aucun outil externe n'est actuellement disponible."

    lines = ["Voici les outils actuellement a ta disposition :"]
    for tool in tools:
        info = getattr(tool, "info", None)
        name = getattr(info, "name", None) or getattr(tool, "__name__", "outil_inconnu")
        raw_schema = getattr(info, "raw_schema", None) or {}
        description = raw_schema.get("description", "").strip()
        short_desc = description.split(".")[0].strip() if description else ""
        if short_desc:
            lines.append(f"- {name} : {short_desc}.")
        else:
            lines.append(f"- {name}")

    return "\n".join(lines)

