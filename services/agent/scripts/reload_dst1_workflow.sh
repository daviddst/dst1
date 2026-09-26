#!/usr/bin/env bash
# ==============================================================================
# reload_dst1_workflow.sh
# Emplacement recommande : /volume/dst1-agent/scripts/reload_dst1_workflow.sh
#
# Contournement du bug n8n connu (GitHub #22782 / #21614) : les webhooks
# d'un workflow actif peuvent se desenregistrer silencieusement en memoire
# runtime. Ce script force un cycle PATCH desactivation/reactivation.
#
# Usage :
#   bash reload_dst1_workflow.sh <WORKFLOW_ID> [path1 path2 ...]
#
# Exemple :
#   bash reload_dst1_workflow.sh v3OLxkzFhslNdaOO dst1-lister-calendriers dst1-consulter-agenda dst1-create-rdv dst1-modifier-rdv dst1-supprimer-rdv
#
# Si aucun path de webhook n'est fourni, l'etape de verification est ignoree.
# ==============================================================================
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/docker/.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERREUR : fichier .env introuvable a $ENV_FILE"
  echo "Definis la variable ENV_FILE si son emplacement est different :"
  echo "  ENV_FILE=/chemin/vers/.env bash reload_dst1_workflow.sh ..."
  exit 1
fi

# Charge les variables du .env dans l'environnement du script
set -a
source "$ENV_FILE"
set +a

: "${N8N_API_KEY:?N8N_API_KEY manquant dans $ENV_FILE}"
#N8N_API_BASE="${N8N_API_BASE:-http://localhost:5678/api/v1}"
N8N_API_BASE="http://localhost:5678/api/v1"

if [ $# -lt 1 ]; then
  echo "Usage : bash reload_dst1_workflow.sh <WORKFLOW_ID> [webhook_path1 webhook_path2 ...]"
  exit 1
fi

WORKFLOW_ID="$1"
shift
WEBHOOK_PATHS=("$@")

echo ">>> Workflow cible : $WORKFLOW_ID"
echo ">>> Desactivation du workflow (via PATCH)..."
curl -s -X PATCH "${N8N_API_BASE}/workflows/${WORKFLOW_ID}" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"active": false}' > /dev/null

sleep 2

echo ">>> Reactivation du workflow (via PATCH)..."
curl -s -X PATCH "${N8N_API_BASE}/workflows/${WORKFLOW_ID}" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"active": true}' > /dev/null

sleep 2

if [ ${#WEBHOOK_PATHS[@]} -eq 0 ]; then
  echo ">>> Aucun webhook a verifier (aucun path fourni). Termine."
  exit 0
fi

echo ">>> Verification des ${#WEBHOOK_PATHS[@]} webhook(s)..."
all_ok=true
for path in "${WEBHOOK_PATHS[@]}"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:5678/webhook/$path" -H "Content-Type: application/json" -d '{}')
  if [ "$code" == "404" ]; then
    echo "  - $path : HTTP $code  <-- ENCORE EN ECHEC (webhook non enregistre)"
    all_ok=false
  else
    echo "  - $path : HTTP $code  (OK)"
  fi
done

echo ""
if [ "$all_ok" = true ]; then
  echo ">>> Tous les webhooks sont correctement enregistres."
else
  echo ">>> ATTENTION : au moins un webhook est toujours introuvable apres le cycle PATCH."
fi
