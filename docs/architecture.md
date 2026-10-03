# Architecture DST1

## Composants et flux

- `dst1-web` : façade FastAPI et interface Web, publiée sur le port 8080.
- `dst1-agent` : worker LiveKit/Gemini ; son endpoint texte écoute sur 8090 et
	est consommé par la façade Web sur le réseau Docker.
- `dst1-n8n` : orchestration et webhooks, publiée sur le port 5678.
- `dst1-postgres` : PostgreSQL/pgvector pour les données DST1, publié sur 5432.
- `evolution-api` et `evolution-postgres` : intégration WhatsApp.
- `whatsapp-redis` : cache Redis WhatsApp, publié sur 63790.
- `whisper` : transcription, publiée sur 8001.

Le navigateur appelle `dst1-web`, qui signe les tokens LiveKit, relaie les
requêtes texte et expose le flux de logs. L’agent découvre les workflows n8n
actifs portant le tag `dst1-tool`, puis appelle leurs webhooks. L’endpoint
texte redécouvre les tools à chaque requête ; le worker vocal les découvre au
préchauffage de ses processus.

## Persistance et source de vérité

`docker/docker-compose.yml` est le Compose versionné. Il monte les sources
runtime depuis `/volume/dst1-agent` et `/volume/dst1-web`, et monte l’état n8n
depuis `/volume/dst1-n8n/data`. Le Compose courant commente les variables de
connexion PostgreSQL de n8n : ne pas supposer que n8n utilise la base
`n8n` créée par l’initialisation PostgreSQL. Vérifier la configuration runtime
avant une migration ou une opération sur les bases.

Correspondances actuelles :

- `services/agent/` -> `/volume/dst1-agent/` (`/app` dans le conteneur).
- `services/web/` -> `/volume/dst1-web/` (`/app` dans le conteneur).
- `docker/docker-compose.yml` -> `/etc/docker/docker-compose.yml`.
- `docker/build/` -> contexte de build sous `/etc/docker/build/`.
- `n8n/workflows/` -> snapshots importés dans l’état n8n ; ce n’est pas un
	volume à synchroniser.

Les volumes `/volume/dst1-agent`, `/volume/dst1-web`, `/volume/dst1-n8n`,
`/volume/dst1-postgres`, `/volume/dst1-logs`, `/volume/evolution-postgres` et
`/volume/whatsapp-redis` ne sont pas des sources Git. Les données n8n et les
credentials sont stockées dans son volume ; ne jamais le copier ni le remplacer
par un export brut.

## Réseau

Le Compose publie directement plusieurs ports, dont ceux de PostgreSQL, n8n,
Web, Evolution API, Redis et Whisper. Une déclaration `ports` sans adresse de
liaison explicite écoute généralement sur les interfaces hôte ; l’exposition
effective dépend aussi du pare-feu et du réseau du serveur. Auditer ces règles
avant de considérer le reverse proxy comme une protection suffisante. Voir
[les notes de sécurité](security-notes.md).
