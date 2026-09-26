# Securite DST1

## Principes

- Le fichier env reel reste exclusivement sur le serveur.
- Les volumes Docker, bases et logs ne vont jamais dans Git.
- Les logs peuvent contenir des arguments et resultats des outils n8n.
- Les secrets exposes hors de leur environnement doivent etre revoques et renouveles.

## Priorites

1. Restreindre le CORS de dst1-web.
2. Proteger endpoint token.
3. Auditer les ports publies : 5432, 5678, 8080, 8089, 63790 et 8001.
4. Utiliser un reverse proxy HTTPS.
5. Prevoir rotation des secrets et sauvegardes testees.
6. Ajouter une confirmation technique pour les actions sensibles.
