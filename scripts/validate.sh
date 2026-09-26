#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Validation Python"

PYTHON_FILES=(
  services/agent/agent.py
  services/agent/text_endpoint.py
  services/agent/tool_loader.py
  services/web/server.py
)

for file in "${PYTHON_FILES[@]}"; do
  if [[ -f "$file" ]]; then
    python3 -m py_compile "$file"
    echo "OK Python : $file"
  fi
done

echo
echo "==> Validation JSON des workflows n8n"

if command -v jq >/dev/null 2>&1; then
  while IFS= read -r -d '' file; do
    jq empty "$file"
    echo "OK JSON : $file"
  done < <(find n8n/workflows -type f -name '*.json' -print0)
else
  echo "INFO : jq absent ; validation JSON ignorée."
fi

echo
echo "==> Validation Docker Compose"

if command -v docker >/dev/null 2>&1 && [[ -f docker/docker-compose.yml ]]; then
  docker compose \
    --env-file .env.example \
    -f docker/docker-compose.yml \
    config --quiet

  echo "OK Compose"
else
  echo "INFO : Docker ou docker/docker-compose.yml absent ; validation Compose ignorée."
fi

echo
echo "==> Fichiers restant à copier manuellement"
find . -type f -name '*.A_COPIER' -print | sort || true

echo
echo "==> Recherche de fichiers sensibles suivis par Git"

if git ls-files | grep -Ei \
'(^|/)(\.env|.*\.pem|.*\.key|.*\.p12|.*\.pfx|.*\.db|.*\.sqlite|.*\.log)$'
then
  echo "ERREUR : fichier potentiellement sensible suivi par Git." >&2
  exit 1
fi

echo
echo "==> État Git"
git status --short

echo
echo "==> Validation terminée"
