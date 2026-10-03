#!/usr/bin/env bash
#
# Déploiement DST1 ciblé.
# À exécuter uniquement après validation humaine explicite.
#
# Usage :
#   ./scripts/deploy/deploy.sh agent
#   ./scripts/deploy/deploy.sh web
#

set -Eeuo pipefail

REPO_DIR="/srv/dst1/app"
COMPOSE_DIR="/etc/docker"

deploy_agent() {
  echo "==> Synchronisation agent vers /volume/dst1-agent"

  rsync -a \
    --delete \
    --exclude=".env" \
    --exclude="logs/" \
    --exclude="__pycache__/" \
    --exclude="*.pyc" \
    "$REPO_DIR/services/agent/" \
    /volume/dst1-agent/

  echo "==> Redémarrage dst1-agent"
  cd "$COMPOSE_DIR"
  docker compose restart dst1-agent

  echo "==> Vérification health endpoint agent"
  for attempt in $(seq 1 15); do
    if docker compose exec -T dst1-agent python -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=3)" \
      >/dev/null 2>&1; then
      echo "OK : dst1-agent est sain"
      return 0
    fi

    echo "Attente dst1-agent : ${attempt}/15"
    sleep 2
  done

  echo "ERREUR : health check dst1-agent en échec" >&2
  return 1
}

deploy_web() {
  echo "==> Synchronisation Web vers /volume/dst1-web"

  rsync -a \
    --delete \
    --exclude=".env" \
    --exclude="logs/" \
    --exclude="__pycache__/" \
    --exclude="*.pyc" \
    "$REPO_DIR/services/web/" \
    /volume/dst1-web/

  echo "==> Redémarrage dst1-web"
  cd "$COMPOSE_DIR"
  docker compose restart dst1-web

  echo "==> Vérification endpoint Web"
  for attempt in $(seq 1 15); do
    if docker compose exec -T dst1-web python -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/config', timeout=3)" \
      >/dev/null 2>&1; then
      echo "OK : dst1-web est sain"
      return 0
    fi

    echo "Attente dst1-web : ${attempt}/15"
    sleep 2
  done

  echo "ERREUR : health check dst1-web en échec" >&2
  return 1
}

case "${1:-}" in
  agent)
    deploy_agent
    ;;
  web)
    deploy_web
    ;;
  *)
    echo "Usage : $0 {agent|web}" >&2
    exit 2
    ;;
esac
