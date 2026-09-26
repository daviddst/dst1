# Instructions Copilot — DST1

## Contexte

DST1 est un assistant IA auto-hébergé comprenant :

- `services/agent/` : agent Python LiveKit/Gemini ;
- `services/web/` : façade FastAPI et interface Web ;
- `docker/` : Docker Compose, Dockerfiles et dépendances ;
- `n8n/workflows/` : exports JSON n8n sans credentials ;
- `n8n/tool-catalog/` : documentation des outils n8n ;
- `docs/` : documentation et procédures ;
- `scripts/` : validation locale.

## Source de vérité

- Le code de l’agent est sous `services/agent/`.
- Le code Web est sous `services/web/`.
- Les Dockerfiles et `requirements.txt` sont sous `docker/build/`.
- L’orchestration est sous `docker/docker-compose.yml`.
- Les données runtime ne sont pas versionnées.

## Règles absolues

- Ne jamais lire, créer, afficher ou modifier `.env`.
- Ne jamais écrire de clé API, token, mot de passe ou credential dans Git.
- Ne jamais modifier les volumes, logs, sauvegardes, données PostgreSQL ou état n8n.
- Ne jamais supprimer un fichier sans demande explicite.
- Ne jamais exécuter `docker compose down`, `rm`, `prune`, ou une commande destructive.
- Ne jamais redémarrer de conteneur ni synchroniser vers le serveur sans validation explicite.
- Ne jamais exécuter une action externe réelle : email, WhatsApp, agenda, contact ou domotique.
- Pour une modification de plus de deux fichiers : proposer un plan avant de modifier.
- Après chaque modification, exécuter ou demander l’exécution de `make validate`.
- Toujours fournir la liste des fichiers modifiés, les impacts et les risques.

## n8n

Les outils DST1 sont découverts depuis les workflows actifs tagués `dst1-tool`.
Un outil s’appuie sur un Webhook et un nœud aval `ToolSchema...`.
Ne jamais versionner de credentials n8n.

## Style

- Python : code lisible, typé quand cela améliore la clarté.
- Conserver la compatibilité avec le runtime Docker existant.
- Préférer de petites modifications réversibles.
- Répondre en français.