#!/usr/bin/env bash
#
# Diagnostic non destructif DST1.
#
# Usage :
#   ./scripts/deploy/diagnose.sh
#   ./scripts/deploy/diagnose.sh dst1-agent
#

set -Eeuo pipefail

COMPOSE_DIR="/etc/docker"
SERVICE="${1:-}"

cd "$COMPOSE_DIR"

echo "==> Etat des services"
docker compose ps

if [[ -n "$SERVICE" ]]; then
  echo
  echo "==> Logs : $SERVICE"
  docker compose logs --tail=150 "$SERVICE"
  exit 0
fi

for service in dst1-agent dst1-web dst1-n8n; do
  echo
  echo "==> Logs : $service"
  docker compose logs --tail=80 "$service"
done
