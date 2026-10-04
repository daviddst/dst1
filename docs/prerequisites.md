# Prérequis DST1

Ce document liste ce dont DST1 dépend. Les valeurs réelles vont dans
`/etc/docker/.env` (jamais dans Git) ; voir `.env.example` pour les noms.

## Infrastructure

- Hôte Linux avec Docker et Docker Compose ; runtime piloté depuis `/etc/docker`,
  état persistant sous `/volume`.
- Services conteneurisés du Compose : `dst1-postgres` (pgvector), `dst1-n8n`,
  `dst1-agent`, `dst1-web`, `evolution-api` avec `evolution-postgres` et
  `whatsapp-redis`, `whisper` (faster-whisper-server).
- Serveur LiveKit joignable (`LIVEKIT_URL`) avec une paire clé/secret.

## Services externes et variables

| Service | Usage | Variables |
|---|---|---|
| Evolution API | Passerelle WhatsApp (messages, groupes, instance) | `EVOLUTION_API_KEY`, `EVOLUTION_BASEURL`, `EVOLUTION_INSTANCE`, `EVOLUTION_POSTGRES_*`, `WA_GROUP_BOT_HOME`, `WA_GROUP_BOT_DAVID` |
| LiveKit | Voix temps réel de l'agent | `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` |
| Google Gemini | Modèle de l'agent et du diagnostic | `GOOGLE_API_KEY` |
| Whisper | Transcription audio | `WHISPER_BASEURL` |
| n8n | Tools et workflows ; API interne | `N8N_API_KEY`, `N8N_API_BASE`, `N8N_WEBHOOK_BASE`, `WEBHOOK_URL`, `N8N_ENCRYPTION_KEY`, `DST1_TOOL_TAG` |
| GAIA | Modèle utilisé par WFBuilder | `GAIA_ROOTURL`, `GAIA_APIKEY`, `GAIA_MODEL` |
| Pushbullet | Notifications (tool `dst1-envoyer-pushbullet`) | `PUSHBULLET_APIKEY` |
| CallMeBot | Notifications/appels | `CALLMEBOT_API_KEY`, `CALLMEBOT_URL` |
| PRIM Île-de-France Mobilités | Transports | `PRIM_URL`, `PRIM_IDFMOBILITE_API_KEY` |
| Google (Calendar, Gmail, Contacts) | Tools agenda, mail, contacts | Credentials OAuth2 configurés dans n8n (hors Git) |

## Configuration n8n

- `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` : requis pour lire `$env.*` dans les nœuds.
- Data Tables WFBuilder : `WFBUILDER_SESSION_TABLE_ID`, `WFBUILDER_AUDIT_TABLE_ID`.
- Credentials n8n à associer manuellement après import des workflows.

## Rappel

`dst1-n8n` lit `/etc/docker/.env` via `env_file` uniquement à la création du
conteneur : après ajout d'une variable, recréer le service (voir le
[runbook](runbook.md)).
