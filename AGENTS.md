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
