# Exports de workflows n8n

Les fichiers JSON de ce répertoire sont des snapshots nettoyés, destinés à la
revue et à l’import explicite. Ils ne reflètent pas automatiquement les
modifications runtime. En particulier, `active` dans un export peut différer
de l’activation dans l’instance.

## Contrôles locaux

Depuis la racine du dépôt, lancer `bash scripts/validate.sh`. Cette validation
parse les JSON, compile les sources Python et vérifie Compose, mais ne valide
pas les expressions ou le comportement des nœuds n8n. Aucun environnement de
staging n’est configuré dans le dépôt.

## Notifications planifiées

Trois exports indépendants, sans tag `dst1-tool` ni nœud `ToolSchema`, sont
préparés pour l’import manuel :

- `notification_agenda_hebdomadaire.json` : dimanche à 20 h, événements de la
  semaine à venir (lundi-dimanche) des calendriers principal, Maud et commun.
- `notification_agenda_quotidienne.json` : chaque jour à 8 h, événements du
  jour de tous les calendriers lisibles ; aucune notification si la liste est
  vide. Les occurrences récurrentes `Danse Sarah` et `Gym Emma` sont exclues.
  Les événements ordinaires sont en gras ; anniversaires et fêtes sont en
  italique, sans gras. Chaque message commence par un emoji.
- `notification_sortie_bacs.json` : marron lundi à 20 h, vert jeudi à 20 h,
  jaune un mercredi sur deux à 20 h, à partir du 7 octobre 2026.

Les exports sont désactivés et utilisent le fuseau `Europe/Paris`. Avant
l’activation manuelle dans n8n, vérifier les noms des calendriers, la
correspondance `MyBot Home` dans la Data Table `whatsapp_group_name` et les
credentials Google Calendar et variables Evolution API. Aucun envoi ne doit
être testé vers le groupe réel pendant la validation locale.

## Détection des perturbations RER D

`tool_verifier_perturbations_rer_d.json` est un Tool n8n identifié par le tag
`dst1-tool`. Il retourne les prochains trains RER D entre Yerres et Gare de
Lyon, leurs heures de départ et d'arrivée prévues, ainsi que les retards ou
suppression détectés dans l'heure glissante à partir de l'appel.

Son seul paramètre est le sens (`yerres_gare_de_lyon` ou
`gare_de_lyon_yerres`). Si l'utilisateur ne le précise pas, l'agent le demande ;
pour une demande « en ce moment » générique, le défaut est Yerres vers Gare de
Lyon le matin et Gare de Lyon vers Yerres l'après-midi. Les arrêts et la ligne
sont configurés depuis le référentiel IDFM : Yerres
(`IDFM:monomodalStopPlace:43226`), Gare de Lyon
(`IDFM:monomodalStopPlace:470195`) et RER D (`IDFM:C01728`).

Le nœud PRIM utilise `PRIM_URL` (ou l'URL stop-monitoring par défaut) et le
header `apikey` issu de `PRIM_IDFMOBILITE_API_KEY`. Le filtre de destination
utilise les `OnwardCalls` de SIRI pour ne garder que les trains desservant la
gare d'arrivée. `stop-monitoring` fournit le temps réel, pas l'historique des
trains déjà passés ; une réponse sans train correspondant ne garantit pas
l'absence de perturbations non publiées dans le flux.

## WFBuilder sur une autre instance

Le projet autonome et ses neuf snapshots sont dans `/srv/WFBuilder`. Depuis
l’instance source, exporter les workflows par leur nom stable :

```bash
cd /srv/WFBuilder
N8N_API_BASE=... N8N_API_KEY=... bash scripts/export-wfbuilder.sh
```

Le script actualise `/srv/WFBuilder/workflows/`, même si les IDs n8n ont changé.
Les exports ne contiennent pas les secrets des credentials. Le dossier contient
aussi son propre guide d’installation.

Après import sur une autre instance, créer les Data Tables puis renseigner
les variables ci-dessous dans le `.env` chargé par le conteneur n8n
(`env_file`), et recréer le conteneur pour qu'il les prenne en compte. Les
workflows n'ont aucune valeur de repli ni credential n8n : tout passe par
ces variables.

| Variable | WF | Rôle |
|---|---|---|
| `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` | tous | Autorise `$env` dans les nœuds (sinon rien ne fonctionne) |
| `N8N_API_BASE` | WF1-WF9 | URL de l'API publique n8n vue depuis le conteneur (ex. `http://dst1-n8n:5678/api/v1`) |
| `N8N_API_KEY` | WF1-WF9 | Clé API n8n envoyée en en-tête `X-N8N-API-KEY` (remplace le credential `Header N8N-API-KEY`) |
| `WEBHOOK_URL` | WF1, WF2 | URL publique de n8n pour les liens du chat (ex. `http://hote:5678/`) |
| `GAIA_ROOTURL`, `GAIA_APIKEY`, `GAIA_MODEL` | WF3, WF7 | Passerelle LLM compatible Anthropic Messages |
| `wf_copilot_sessions` | WF1, WF2, WF6 | Data Table de session résolue par son nom |
| `audit_log` | WF9 | Data Table d'audit résolue par son nom |

Les sous-workflows sont liés par leur **nom** et non par leur ID : WF1, WF2,
WF3 et WF7 résolvent au démarrage les IDs via `GET /workflows?name=...`
(nœuds `Noms WFBuilder` → `Résoudre IDs WFBuilder` → `Restaurer Entrée`).
Les noms `WFBuilder - WF3 …` à `WFBuilder - WF9 …` doivent donc rester
inchangés et uniques sur l'instance ; un nom absent ou dupliqué lève une erreur
explicite.

Data Tables (colonnes de type string) :

- `wf_copilot_sessions` : `session_id`, `mode`, `target_workflow_ids`,
  `messages`, `tools_schema`, `status`, `backups`
- `audit_log` : `session_id`, `action`, `target_id`, `timestamp`, `result`,
  `diff_summary`

Ordre d'installation : importer les workflows sans les renommer ; créer les
Data Tables manquantes avec `bash scripts/create-data-tables.sh` depuis
`/srv/WFBuilder` ; recréer le conteneur n8n si son environnement change ;
activer WF1 et WF2 (webhooks). Le script découvre le projet par les noms des
workflows WFBuilder et vérifie les colonnes des tables existantes. Les nœuds
Data Table résolvent les tables par leur nom, sans ID à configurer. La clé
`N8N_API_KEY` est lue en clair par les nœuds HTTP : la restreindre à l'instance
et la régénérer en cas de fuite.

`.env.example` documente ces variables sans contenir de valeurs réelles.

Le lien renvoyé par WF1 ouvre la page GET `/webhook/wf-copilot/chat-ui`; celle-ci
transmet les messages au webhook POST `/webhook/wf-copilot/chat` et conserve le
`sessionId` de la Data Table.

## Import contrôlé

Avant import, vérifier le diff du JSON, les nœuds et connexions, le schéma
`ToolSchema`, le tag `dst1-tool`, les chemins de webhook et les références de
credential. N’inclure aucun secret, exécution, payload personnel ou export brut
de volume. Lier les credentials dans n8n, vérifier les doublons, activer
explicitement le workflow et redémarrer `dst1-agent` si un tool a changé.

Les tests d’actions doivent s’arrêter avant le nœud externe ou utiliser des
simulations. Envoi de mail, WhatsApp, modification de contact et agenda réels
nécessitent une validation explicite distincte.
