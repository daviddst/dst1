# Runbook DST1

## Avant modification

Depuis `/srv/dst1/app` :

        git status --short
        bash scripts/validate.sh

Le Makefile courant ne contient pas de recette `validate` : `make validate`
est actuellement une cible vide et n’exécute pas le script. La checklist se
lance avec `bash scripts/manual-copy-checklist.sh`.

## Apres synchronisation serveur explicitement validee

Le code exécuté est monté depuis `/volume`, pas copié dans l’image. Pour un
nouveau workflow n8n actif/tagué `dst1-tool`, redémarrer `dst1-agent` afin que
les workers vocaux redécouvrent les outils. L’endpoint texte les redécouvre à
chaque requête. Le redémarrage de n8n n’est pas nécessaire pour un simple
import/activation de workflow.

Pour les changements agent, depuis `/etc/docker` :

    cd /etc/docker
    docker compose restart dst1-agent

Pour les changements Web :

    cd /etc/docker
    docker compose restart dst1-web

Une modification du seul fichier statique Web peut nécessiter uniquement un
rechargement navigateur.

Après un redémarrage, contrôler l’état et le health check du service, puis lire
ses logs. Pour l’agent, le health endpoint interne est
`http://127.0.0.1:8090/health` depuis le conteneur. Vérifier aussi dans les logs
que le tool attendu a été découvert.

## Import n8n

Les exports sont importés explicitement ; aucun environnement de staging n’est
défini dans ce dépôt. Avant activation, vérifier le nom, le webhook, le tag
`dst1-tool`, le schéma, les références de credential et l’absence de doublon.
Associer les credentials dans n8n sans exporter de secret, activer le workflow,
puis redémarrer `dst1-agent` si l’outil doit être disponible dans le worker
vocal. Ne pas tester l’envoi d’un message réel dans le cadre de la validation.

Le `active` de l’export est un instantané et peut différer de l’état n8n. La
mise à jour du JSON Git ne désactive pas automatiquement le workflow runtime.

## Dépannage : variable d'environnement absente dans n8n (ex. Pushbullet 500)

Symptôme : le webhook `dst1-envoyer-pushbullet` renvoie 500 « Error in workflow »
et les logs `dst1-n8n` montrent un 401 `invalid_access_token` de Pushbullet.

Cause : `dst1-n8n` charge `/etc/docker/.env` via `env_file`, lu uniquement à la
création du conteneur. Une variable ajoutée au `.env` (ex. `PUSHBULLET_APIKEY`)
n'est pas visible tant que le conteneur n'est pas recréé ; un simple `restart`
ne suffit pas.

Vérification (sans afficher la valeur) :

    docker exec dst1-n8n sh -c 'test -n "$PUSHBULLET_APIKEY" && echo defined || echo MISSING'

Correction (validation explicite requise) :

    docker compose -f /etc/docker/docker-compose.yml up -d dst1-n8n

Rollback : aucun changement de compose n'est nécessaire ; retirer la variable du
`.env` et recréer le conteneur.

## Rollback

- Tool n8n nouvellement créé : le désactiver puis supprimer uniquement son ID ;
    ne pas modifier les autres workflows.
- Code agent/Web : restaurer la version précédente après revue du diff, puis
    redémarrer uniquement le service concerné et revalider son health check.
- Ne jamais lancer une synchronisation complète sans examiner ses effets : le
    script `scripts/deploy/deploy.sh` emploie `rsync --delete` sur le répertoire
    cible.

## Interdit sans plan, sauvegarde et validation

    docker compose down
    docker system prune
    docker volume prune
