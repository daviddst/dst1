# WA Main Router

## Références

- **Fichier Git :** `n8n/workflows/WA Main Router.json`
- **Système concerné :** WhatsApp / Evolution API / DST1
- **Objectif :** à compléter après audit du workflow
- **Statut :** à auditer

## Déclencheur

- Type : Webhook / autre
- Chemin : à compléter
- Méthode HTTP : à compléter

## Outils DST1 exposés

| Nom du tool | Webhook | Description | Confirmation requise | Risque |
|---|---|---|---|---|
| À compléter | À compléter | À compléter | Oui / Non | Faible / Moyen / Élevé |

## Données manipulées

- Numéro ou identifiant WhatsApp : oui / non
- Contenu de message : oui / non
- Identifiant de groupe : oui / non
- Données de contact : oui / non

## Tests prévus

1. Test sans action externe.
2. Test de validation de schéma.
3. Test d’action simulée.
4. Test d’échec et réponse utilisateur.
5. Test de confirmation pour action sensible.

## Rollback

- Désactiver le workflow dans n8n.
- Restaurer le JSON Git précédent.
- Réimporter une version validée si nécessaire.
