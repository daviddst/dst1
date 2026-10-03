# Instructions Copilot — DST1

## Contexte
Projet : `services/agent/` (Python/LiveKit/Gemini), `services/web/` (FastAPI), `docker/`, `n8n/`.

## Règles absolues & Token Economy
- **Réponses ultra-concises** : zéro politesse, pas de résumés d'introduction/conclusion, uniquement le code ou la réponse directe.
- **Contexte restreint** : N'envoie/ne modifie que la fonction, la ligne ou le nœud n8n concerné. Ne lis/n'inclus JAMAIS un fichier entier si seule une sous-partie suffit.
- **Interdictions** : Ne jamais supprimer de fichier, modifier de volume/logs/PostgreSQL/n8n state, ni exécuter de commandes destructives (`docker compose down`, `rm`, `prune`).
- **Aucune action externe** : Pas d'emails, WhatsApp, agenda, domotique.
- **Validation** : Toujours lancer `make validate` après modification.

## Structure
- Code agent : `services/agent/` | Web : `services/web/`
- Docker : `docker/build/` & `docker/docker-compose.yml`
- n8n : Workflows tagués `dst1-tool` (Webhook + `ToolSchema...`). **Zero credentials**.

## Style de Code
- Python typé, concis, modulaire. Modifications petites et réversibles.
- Réponses en français.