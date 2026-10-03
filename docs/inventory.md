# Inventaire DST1

## Sources versionnées

- `services/agent/` : code agent, endpoint texte, loader et configuration.
- `services/web/` : façade FastAPI et ressources statiques.
- `docker/docker-compose.yml` : définition d’orchestration du dépôt.
- `docker/build/` : Dockerfiles, dépendances et initialisation PostgreSQL.
- `n8n/workflows/` : exports JSON de workflows, à traiter comme snapshots.
- `n8n/tool-catalog/`, `docs/` et `scripts/` : documentation et procédures.

## Cibles runtime

- `services/agent/` -> `/volume/dst1-agent/`.
- `services/web/` -> `/volume/dst1-web/`.
- Compose -> `/etc/docker/docker-compose.yml`.
- Définitions de build -> `/etc/docker/build/`.
- Workflows -> import explicite dans n8n ; pas de copie vers son volume.

Les scripts de déploiement ne sont pas équivalents : `scripts/deploy/deploy.sh`
recopie un répertoire complet avec `rsync --delete`. Examiner le diff et les
fichiers runtime additionnels avant toute utilisation.

## Données runtime à ne pas copier ni versionner

- `/volume/dst1-n8n/` : état n8n, credentials et données d’exécution.
- `/volume/dst1-postgres/` et `/volume/evolution-postgres/` : bases de données.
- `/volume/dst1-logs/` : logs pouvant contenir arguments, résultats ou données
	personnelles.
- `/volume/whatsapp-redis/` : état Redis.
- Autres volumes de services : configuration, cache, médias ou données privées.

Ne jamais lire, synchroniser, exporter vers Git ou supprimer ces données sans
procédure et autorisation spécifiques.
