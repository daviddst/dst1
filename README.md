# DST1 - Digital Smart Technician One

Dépôt source et documentation du système DST1. Dans l’environnement serveur
actuel, le dépôt se trouve dans `/srv/dst1/app`; le runtime Docker est piloté
séparément depuis `/etc/docker` et conserve son état sous `/volume`.

## Composants

- `services/agent/` : agent LiveKit/Gemini et endpoint texte interne.
- `services/web/` : façade FastAPI, interface Web et relais vers l’agent.
- `docker/` : Compose et définitions de build versionnées.
- `n8n/` : exports de workflows nettoyés et catalogue des tools.
- `docs/` et `scripts/` : procédures, architecture et contrôles.

Le Compose courant configure séparément `dst1-postgres` et `dst1-n8n`. Les
paramètres PostgreSQL de n8n y sont commentés : sauf configuration runtime
différente, n8n utilise donc son stockage SQLite persistant dans son volume.
Voir [l’architecture](docs/architecture.md) avant toute migration de base.

## Validation locale

Depuis la racine du dépôt :

    bash scripts/validate.sh
    bash scripts/manual-copy-checklist.sh
    git status --short

Le Makefile courant n’a pas de recette `validate` ni `checklist` : la commande
`make validate` peut réussir sans rien valider. Les cibles `diagnose`, `logs`,
`deploy-agent` et `deploy-web` sont définies ; les cibles de déploiement
synchronisent les fichiers et redémarrent des services.

## Données et déploiement

Les exports n8n de ce dépôt sont des snapshots, pas une synchronisation
automatique de l’instance. Les credentials, bases, exécutions et logs restent
dans les volumes runtime et ne doivent pas être copiés dans Git. Toute
activation/import n8n, synchronisation serveur ou redémarrage nécessite une
validation humaine explicite. Voir le [runbook](docs/runbook.md) et les
[conventions n8n](docs/n8n-workflow-convention.md).

Ne jamais versionner de secrets, fichiers `.env` réels, données personnelles,
exports bruts de runtime, bases, logs ou sauvegardes. Voir les [notes de
sécurité](docs/security-notes.md) pour les risques connus et les priorités.
