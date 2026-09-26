#!/usr/bin/env bash
# ==============================================================================
# list_dst1_workflows.sh
# Emplacement recommande : /volume/dst1-agent/scripts/list_dst1_workflows.sh
#
# Liste tous les workflows n8n avec leur ID, statut actif/inactif et tags.
# Utile pour verifier rapidement qu'un workflow porte bien le tag attendu
# (dst1-tool pour la decouverte automatique par l'agent, dst1-tool-managed
# pour les workflows crees par l'outil meta-workflow).
#
# Usage :
#   bash list_dst1_workflows.sh                # liste tous les workflows
#   bash list_dst1_workflows.sh dst1-tool       # filtre par tag
#   bash list_dst1_workflows.sh dst1-tool-managed
# ==============================================================================
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/docker/.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERREUR : fichier .env introuvable a $ENV_FILE"
  echo "Precise son emplacement reel via : ENV_FILE=/chemin/.env bash $0"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

: "${N8N_API_KEY:?N8N_API_KEY manquant dans $ENV_FILE}"

# Ce script s'execute depuis l'hote (hors des conteneurs Docker) : le port
# 5678 est mappe sur l'hote via docker-compose.yml, donc localhost fonctionne
# ici, contrairement a N8N_API_BASE (dst1-n8n:5678) qui n'est resolvable que
# depuis l'interieur du reseau Docker.
N8N_API_BASE="http://localhost:5678/api/v1"

TAG_FILTER="${1:-}"

if [ -n "$TAG_FILTER" ]; then
  URL="${N8N_API_BASE}/workflows?tags=${TAG_FILTER}"
  echo ">>> Workflows filtres sur le tag '${TAG_FILTER}' :"
else
  URL="${N8N_API_BASE}/workflows"
  echo ">>> Tous les workflows :"
fi

echo ""

curl -s "$URL" -H "X-N8N-API-KEY: ${N8N_API_KEY}" | python3 -c "
import json, sys

try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    print('ERREUR : reponse invalide de l API n8n (verifier N8N_API_KEY / connectivite).')
    sys.exit(1)

workflows = data.get('data', [])

if not workflows:
    print('Aucun workflow trouve.')
    sys.exit(0)

print(f\"{'ID':<20} | {'ACTIF':<6} | {'TAGS':<40} | NOM\")
print('-' * 100)

for wf in workflows:
    tags = ', '.join(t['name'] for t in wf.get('tags', []) or [])
    actif = '[X]' if wf.get('active') else '[ ]'
    print(f\"{wf['id']:<20} | {actif:<6} | {tags:<40} | {wf['name']}\")

print('')
print(f\"Total : {len(workflows)} workflow(s)\")
"

