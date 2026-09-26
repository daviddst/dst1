# ADR-0001 — Séparation dépôt Git et runtime Docker

## Statut

Accepté.

## Contexte

Le serveur actuel exécute Docker Compose depuis `/etc/docker` et stocke son
état persistant sous `/volume`.

Le dépôt Git local est sous :

`/Users/david/Projets/DST1`

## Décision

Le dépôt Git est la source de vérité pour :

- Docker Compose ;
- Dockerfiles ;
- requirements ;
- sources de l'agent ;
- sources Web ;
- scripts SQL d'initialisation ;
- exports n8n nettoyés ;
- documentation.

Les volumes Docker restent la source de vérité runtime pour :

- données PostgreSQL ;
- état n8n ;
- credentials n8n ;
- logs ;
- caches ;
- sessions ;
- données de conversation.

## Conséquence

Une future procédure de déploiement devra synchroniser explicitement :

- `services/agent/` vers `/volume/dst1-agent/`
- `services/web/` vers `/volume/dst1-web/`
- `docker/build/` vers `/etc/docker/build/`
- `docker/docker-compose.yml` vers `/etc/docker/docker-compose.yml`

Aucune synchronisation ou aucun redémarrage ne doit être automatique à ce stade.
