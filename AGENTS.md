# Regles pour les agents IA DST1

## Mission

Aider a analyser, proposer, modifier, tester et documenter le projet DST1.

## Organisation

- services/agent : agent LiveKit Gemini et endpoint texte
- services/web : facade FastAPI et interface Web
- infra/docker : Docker Compose
- build : Dockerfiles et dependances apres audit
- n8n/workflows : exports JSON sans credentials
- docs : documentation
- scripts : validations et operations reproductibles

## Regles absolues

1. Analyser avant toute modification.
2. Poser seulement les questions bloquantes.
3. Proposer un plan avant de modifier plus de deux fichiers.
4. Ne jamais lire, afficher, ecrire ou versionner des secrets.
5. Ne jamais modifier fichier env, base, volume ou log.
6. Ne jamais deployer ou redemarrer sans validation explicite.
7. Ne jamais lancer docker compose down, rm ou prune.
8. Executer make validate apres modification.
9. Toujours resumer fichiers, tests, impacts et risques.

## Validation obligatoire

Une validation humaine explicite est requise pour :

- commit ou push Git
- synchronisation vers le serveur
- build ou restart Docker
- import ou export n8n reel
- migration de base
- action externe : mail, WhatsApp, agenda, contact ou domotique

## Source de vérité et changements Docker

- Le code agent exécuté via le volume `/app` est sous `services/agent/`.
- Le code Web exécuté via le volume `/app` est sous `services/web/`.
- Les Dockerfiles, requirements et scripts d'initialisation sont sous `docker/build/`.
- Le fichier d'orchestration est `docker/docker-compose.yml`.
- Un Dockerfile ne doit pas dupliquer le code applicatif sauf nécessité explicite
  de bootstrap d'image.
- Avant toute modification, vérifier si le code est injecté par volume ou copié
  dans l'image par le Dockerfile.

## Exécution sur le serveur via VS Code Remote Tunnels

Le dépôt de travail est ouvert dans VS Code depuis le serveur :

`/srv/dst1/app`

L’agent IA peut utiliser sans validation supplémentaire :

- `make validate`
- `make diagnose`
- `make logs SERVICE=dst1-agent`
- `make logs SERVICE=dst1-web`
- `make logs SERVICE=dst1-n8n`
- `git status`
- `git diff`

Les commandes suivantes exigent une validation explicite de l’utilisateur,
obtenue dans la conversation immédiatement avant leur exécution :

- `make deploy-agent`
- `make deploy-web`
- toute commande Docker non prévue par les scripts ;
- toute synchronisation vers `/volume` ;
- toute modification de `/etc/docker/docker-compose.yml` ;
- import de workflow n8n ;
- action externe réelle.

Avant un déploiement, toujours présenter :
1. les fichiers modifiés ;
2. le diff Git ;
3. le composant concerné ;
4. les tests prévus ;
5. la procédure de rollback.

Après un déploiement :
1. vérifier le health check ;
2. afficher les logs du service concerné ;
3. résumer le résultat ;
4. proposer le rollback en cas d'échec.
