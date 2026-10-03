# Modifier un contact Google

## Références

- **Workflow :** `n8n/workflows/tool_modifier_contact_google.json`
- **Nom du tool :** `modifier_contact_google`
- **Webhook :** `dst1-modifier-contact-google`
- **Fournisseur :** Google Contacts / People API

## Contrat

- `resource_name` : identifiant `people/...` retourné par `rechercher_contacts_google`.
- `updates` : objet de champs Google People API à modifier, avec les valeurs complètes souhaitées.
- Les champs absents de `updates` ne sont pas modifiés.
- Chaque champ présent remplace sa valeur complète; pour les champs de type liste, fournir toutes les entrées à conserver. Une liste vide demande l'effacement de ce champ.
- Les champs en lecture seule ou gérés par Google, comme `metadata` et `resourceName`, sont rejetés.

Tous les champs de contact modifiables par `people.updateContact` sont acceptés : adresses, biographies, anniversaires, calendriers, données client, e-mails, événements, identifiants externes, genres, clients de messagerie, intérêts, langues, lieux, appartenances, mots-clés, noms, surnoms, professions, organisations, téléphones, relations, adresses SIP, URL et champs définis par l'utilisateur.

## Confirmation

Avant d'appeler le tool, DST1 doit présenter le contact visé et le récapitulatif exact des champs et nouvelles valeurs, puis attendre une confirmation explicite. Un refus ou une absence de confirmation signifie qu'aucun appel n'est effectué. Cette règle est conversationnelle; `require_confirmation` n'est pas un verrou technique dans le chargeur actuel.

## Configuration et vérifications

- Le script `scripts/deploy/deploy-n8n-contact-tool.sh` crée un workflow autonome et distinct par `POST`. Le workflow de recherche n'est lu que pour reprendre sa credential OAuth et son tag; il n'est jamais modifié.
- Vérifier que cette credential possède le scope d'écriture Contacts. Le déploiement exige alors `DST1_GOOGLE_CONTACTS_WRITE_SCOPE_CONFIRMED=true` et `N8N_API_KEY` dans l'environnement; le secret n'est ni affiché ni lu depuis un fichier.
- `--dry-run` prépare le payload sans réseau. `--apply` refuse les doublons, crée le workflow, vérifie son tag et son webhook, puis l'active. `--rollback WORKFLOW_ID` désactive et supprime uniquement le workflow autonome.
- Vérifier la validation des champs et les erreurs avec des requêtes simulées. Ne pas tester d'écriture sur le carnet de contacts réel sans autorisation explicite.