# Conventions n8n DST1

Les exports de workflows sont placés dans `n8n/workflows/` au format JSON.
Ce sont des snapshots de l’instance, pas une synchronisation bidirectionnelle.
Un champ `active` dans un fichier peut différer de l’état runtime.

## Export et import

Ne jamais versionner :

- credentials
- tokens
- clés
- executions
- données personnelles ou métadonnées de compte inutiles
- contenu du volume n8n

Les références n8n de credential peuvent contenir un identifiant et un nom,
mais jamais le secret. Les vérifier et nettoyer les métadonnées non nécessaires
avant de committer un export. Aucun environnement de staging n’est défini dans
le dépôt : l’import en production nécessite une validation humaine explicite.

## Convention outils DST1

Un workflow decouvert comme outil doit :

1. etre actif
2. porter le tag dst1-tool
3. comporter un noeud Webhook
4. comporter un noeud aval dont le nom commence par ToolSchema
5. definir tool_name, tool_description, tool_parameters et require_confirmation

Le chargeur suit les connexions du webhook jusqu’au premier `ToolSchema*` et
lit les workflows actifs portant le tag `dst1-tool`. Après activation d’un
nouveau workflow, redémarrer `dst1-agent` pour que les workers vocaux
redécouvrent la liste. L’endpoint texte effectue sa découverte à chaque requête.

**Important :** `require_confirmation` est actuellement une métadonnée de
catalogue, pas un verrou d’exécution. Le loader ne l’injecte pas dans le schéma
appelable et l’endpoint texte exécute directement les appels de fonction. Une
description de tool ou un prompt demandant confirmation ne protège pas contre
un appel erroné du modèle. Toute action sensible doit avoir une vérification
technique côté application avant son effet externe.

Documenter chaque outil dans `n8n/tool-catalog/`. Décrire les paramètres
obligatoires, credentials requises, confirmation, impact externe, tests sans
effet et rollback. Ne pas tester un envoi ou une modification réelle pendant la
validation d’un export.
