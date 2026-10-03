#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTACTS_FILE="$ROOT_DIR/n8n/workflows/tool_rechercher_dans_google_contacts__SyqKNj1zfNP0NlCU.json"
TOOL_FILE="$ROOT_DIR/n8n/workflows/tool_modifier_contact_google.json"
API_BASE="${N8N_API_BASE:-http://10.42.42.10:5678/api/v1}"
TOOL_WEBHOOK="dst1-modifier-contact-google"
WORKFLOW_NAME="Tool - Modifier contact Google"

usage() {
  echo "Usage: $0 --dry-run | --apply | --rollback BACKUP_FILE" >&2
}

api_request() {
  local method="$1"
  local url="$2"
  local body="${3:-}"
  local response
  local status
  local response_body
  local error_message
  local args=(--silent --show-error --connect-timeout 5 --max-time 30
    --request "$method"
    --header "X-N8N-API-KEY: $N8N_API_KEY"
    --header "Accept: application/json"
    --write-out $'\n%{http_code}')

  if [[ -n "$body" ]]; then
    args+=(--header "Content-Type: application/json" --data-binary "$body")
  fi
  response="$(curl "${args[@]}" "$url")" || return $?
  status="${response##*$'\n'}"
  response_body="${response%$'\n'*}"
  if [[ ! "$status" =~ ^2[0-9][0-9]$ ]]; then
    error_message="$(jq -r '.message // .error // empty' <<< "$response_body" 2>/dev/null || true)"
    echo "API n8n HTTP $status: ${error_message:-requête refusée}" >&2
    return 22
  fi
  printf '%s' "$response_body"
}

build_create_payload() {
  local contacts="$1"
  local credential

  credential="$(jq -ce '
    [.nodes[] | select(.name == "Rechercher dans Google Contacts")
      | .credentials.googleContactsOAuth2Api]
    | unique
    | if length == 1 and .[0] != null then .[0]
      else error("credential Google Contacts unique introuvable")
      end
  ' <<< "$contacts")"

  jq -ce --argjson credential "$credential" '
    {
      name,
      nodes: [.nodes[] | if
        .name == "Google - Lire contact et ETag" or
        .name == "Google - Modifier contact"
        then . + {credentials: {googleContactsOAuth2Api: $credential}}
        else . end],
      connections,
      settings: (.settings // {})
    }
  ' "$TOOL_FILE"
}

find_existing_tool() {
  local cursor=""
  local response
  local found_id=""
  local page_ids

  while true; do
    local args=(--silent --show-error --fail --connect-timeout 5 --max-time 30
      --get
      --header "X-N8N-API-KEY: $N8N_API_KEY"
      --header "Accept: application/json"
      --data-urlencode "limit=250")
    if [[ -n "$cursor" ]]; then
      args+=(--data-urlencode "cursor=$cursor")
    fi

    response="$(curl "${args[@]}" "$API_BASE/workflows")"
    page_ids="$(jq -r --arg name "$WORKFLOW_NAME" \
      '.data[]? | select(.name == $name) | .id' <<< "$response")"
    if [[ -n "$page_ids" ]]; then
      if [[ -n "$found_id" || "$(wc -l <<< "$page_ids")" -gt 1 ]]; then
        echo "Plusieurs workflows nommés '$WORKFLOW_NAME' existent." >&2
        return 2
      fi
      found_id="$page_ids"
    fi

    cursor="$(jq -r '.nextCursor // empty' <<< "$response")"
    [[ -n "$cursor" ]] || break
  done

  printf '%s' "$found_id"
}

rollback_workflow() {
  local workflow_id="$1"
  local workflow
  [[ "$workflow_id" =~ ^[A-Za-z0-9_-]+$ ]] || {
    echo "Identifiant de workflow invalide." >&2
    return 2
  }

  workflow="$(api_request GET "$API_BASE/workflows/$workflow_id")"
  [[ "$(jq -r '.name' <<< "$workflow")" == "$WORKFLOW_NAME" ]] || {
    echo "Le workflow $workflow_id n'est pas le tool de modification attendu; suppression refusée." >&2
    return 1
  }
  if [[ "$(jq -r '.active // false' <<< "$workflow")" == "true" ]]; then
    api_request POST "$API_BASE/workflows/$workflow_id/deactivate" >/dev/null
  fi
  api_request DELETE "$API_BASE/workflows/$workflow_id" >/dev/null
  echo "Workflow autonome $workflow_id désactivé et supprimé."
}

[[ -f "$CONTACTS_FILE" && -f "$TOOL_FILE" ]] || {
  echo "Export Google Contacts ou export du tool introuvable." >&2
  exit 1
}
command -v jq >/dev/null 2>&1 || { echo "jq est requis." >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl est requis." >&2; exit 1; }

case "${1:-}" in
  --dry-run)
    template="$(jq -ce '.' "$CONTACTS_FILE")"
    payload="$(build_create_payload "$template")"
    jq -e --arg name "$WORKFLOW_NAME" \
      '.name == $name and (has("tags") | not) and (has("id") | not)' <<< "$payload" >/dev/null
    echo "Payload POST valide pour un workflow autonome."
    echo "Recherche source: $(jq -r '.id' <<< "$template") (lecture seule); nœuds du nouveau workflow: $(jq '.nodes | length' <<< "$payload"). Aucun appel réseau effectué."
    ;;
  --apply)
    [[ -n "${N8N_API_KEY:-}" ]] || { echo "N8N_API_KEY doit être fourni dans l'environnement." >&2; exit 1; }
    [[ "${DST1_GOOGLE_CONTACTS_WRITE_SCOPE_CONFIRMED:-}" == "true" ]] || {
      echo "Vérifiez que la credential Google Contacts possède le scope d'écriture, puis définissez DST1_GOOGLE_CONTACTS_WRITE_SCOPE_CONFIRMED=true." >&2
      exit 1
    }

    source_id="$(jq -er '.id' "$CONTACTS_FILE")"
    current="$(api_request GET "$API_BASE/workflows/$source_id")"
    [[ "$(jq -r '.name' <<< "$current")" == "Tool - Rechercher dans Google Contacts" ]] || {
      echo "Le workflow distant de recherche ne correspond pas; arrêt sans modification." >&2
      exit 1
    }
    [[ "$(jq -r '.active // false' <<< "$current")" == "true" ]] || {
      echo "Le workflow de recherche Google Contacts n'est pas actif; arrêt." >&2
      exit 1
    }
    jq -e 'any(.tags[]?; .name == "dst1-tool")' <<< "$current" >/dev/null || {
      echo "Le workflow de recherche n'a pas le tag dst1-tool; arrêt." >&2
      exit 1
    }

    existing_id="$(find_existing_tool)"
    [[ -z "$existing_id" ]] || {
      echo "Le workflow autonome existe déjà (ID $existing_id); aucun changement effectué." >&2
      exit 1
    }

    payload="$(build_create_payload "$current")"
    created="$(api_request POST "$API_BASE/workflows" "$payload")"
    workflow_id="$(jq -er '.id // .data.id' <<< "$created")"
    tag_payload="$(jq -ce '[.tags[] | select(.name == "dst1-tool") | {id}]' <<< "$current")"
    if ! api_request PUT "$API_BASE/workflows/$workflow_id/tags" "$tag_payload" >/dev/null; then
      echo "Échec de l'association du tag; suppression du nouveau workflow." >&2
      rollback_workflow "$workflow_id"
      exit 1
    fi
    updated="$(api_request GET "$API_BASE/workflows/$workflow_id")"
    if [[ "$(jq -r '.name' <<< "$updated")" != "$WORKFLOW_NAME" ]] || \
      ! jq -e --arg webhook "$TOOL_WEBHOOK" \
        'any(.nodes[]; .type == "n8n-nodes-base.webhook" and .parameters.path == $webhook) and any(.tags[]?; .name == "dst1-tool")' \
        <<< "$updated" >/dev/null; then
      echo "Le nouveau workflow n'a pas le tag ou le webhook attendu; suppression de ce workflow uniquement." >&2
      rollback_workflow "$workflow_id"
      exit 1
    fi

    if ! api_request POST "$API_BASE/workflows/$workflow_id/activate" >/dev/null; then
      echo "Échec de l'activation; suppression du nouveau workflow." >&2
      rollback_workflow "$workflow_id"
      exit 1
    fi

    updated="$(api_request GET "$API_BASE/workflows/$workflow_id")"
    if [[ "$(jq -r '.active // false' <<< "$updated")" != "true" ]] || \
      ! jq -e --arg webhook "$TOOL_WEBHOOK" \
        'any(.nodes[]; .type == "n8n-nodes-base.webhook" and .parameters.path == $webhook) and any(.tags[]?; .name == "dst1-tool")' \
        <<< "$updated" >/dev/null; then
      echo "Vérification post-activation échouée; suppression du nouveau workflow." >&2
      rollback_workflow "$workflow_id"
      exit 1
    fi

    echo "Workflow autonome créé, tagué et activé (ID $workflow_id)."
    echo "Le workflow de recherche Google Contacts n'a pas été modifié."
    echo "Rollback: $0 --rollback $workflow_id"
    ;;
  --rollback)
    [[ -n "${N8N_API_KEY:-}" ]] || { echo "N8N_API_KEY doit être fourni dans l'environnement." >&2; exit 1; }
    [[ $# -eq 2 ]] || { usage; exit 2; }
    rollback_workflow "$2"
    ;;
  *)
    usage
    exit 2
    ;;
esac