# Architecture DST1

## Composants

- dst1-web : facade FastAPI exposee sur le port 8080
- dst1-agent : agent LiveKit Gemini et endpoint texte interne sur le port 8090
- dst1-n8n : orchestration des outils et workflows
- dst1-postgres : PostgreSQL avec pgvector
- evolution-api : integration WhatsApp
- evolution-postgres : base Evolution API
- whatsapp-redis : Redis
- whisper : transcription audio

## Flux principal

Navigateur vers dst1-web.

dst1-web genere les tokens LiveKit, relaie les requetes texte vers dst1-agent
et expose les logs en streaming.

dst1-agent interroge n8n pour decouvrir les outils portant le tag dst1-tool,
puis appelle les webhooks n8n.

n8n orchestre PostgreSQL, Evolution API, Whisper et les autres integrations.

## Volumes serveur non versionnes

- /volume/dst1-web
- /volume/dst1-agent
- /volume/dst1-n8n
- /volume/dst1-postgres
- /volume/dst1-logs
- /volume/evolution-postgres
- /volume/whatsapp-redis

## Correspondance serveur vers Git

- /etc/docker/docker-compose.yml vers infra/docker/compose.server.yml
- sources agent vers services/agent
- sources Web vers services/web
- Dockerfiles et dependances vers build
- workflows n8n nettoyes vers n8n/workflows
