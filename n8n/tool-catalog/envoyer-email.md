# Envoyer un e-mail

## Références

- **Workflow :** `n8n/workflows/tool_envoyer_email.json`
- **Nom du tool :** `envoyer_email`
- **Webhook :** `dst1-envoyer-email`
- **Fournisseur :** Gmail

## Contrat

- `to` : une adresse e-mail unique.
- `subject` : objet non vide, sans retour à la ligne.
- `body` : corps non vide, envoyé en texte brut.
- Les champs supplémentaires sont refusés.

## Confirmation

Avant tout appel, DST1 doit présenter l'adresse du destinataire, l'objet et le texte intégral du message, puis attendre une confirmation explicite. Un refus, une absence de réponse ou un doute signifie qu'aucun envoi n'est effectué. Cette règle est portée par la description du tool et `require_confirmation`; elle doit être respectée par l'agent.

## Configuration et vérifications

- Le workflow est exporté inactif. À l'import dans n8n, associer au nœud Gmail une credential OAuth Gmail (`gmailOAuth2`) autorisée à envoyer des messages, puis vérifier le tag `dst1-tool` et activer le workflow pour le rendre découvrable par DST1.
- L'export ne contient aucune credential. Ne pas tester l'envoi sur une adresse réelle sans autorisation explicite.
- Vérifier d'abord les erreurs de validation (`to`, `subject` et `body`) sans exécuter le nœud Gmail.