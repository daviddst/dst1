#!/usr/bin/env bash
# export $(cat /etc/docker/.env | xargs -0)

set -euo pipefail

# Export de tous les workflows n8n actifs tagues "dst1-tool".
#
# Variables attendues :
#   N8N_API_BASE=http://dst1-n8n:5678/api/v1
#   N8N_API_KEY=<cle API n8n>
#
# Variables optionnelles :
#   DST1_TOOL_TAG=dst1-tool
#   EXPORT_DIR=/volume/dst1-agent/exports/dst1-tools

N8N_API_BASE="${N8N_API_BASE:-http://dst1-n8n:5678/api/v1}"
N8N_API_KEY="${N8N_API_KEY:-}"
DST1_TOOL_TAG="${DST1_TOOL_TAG:-dst1-tool}"
EXPORT_DIR="${EXPORT_DIR:-/srv/dst1/app/n8n/workflows}"

N8N_API_BASE=http://10.42.42.10:5678/api/v1

if [[ -z "${N8N_API_KEY}" ]]; then
  echo "Erreur : la variable N8N_API_KEY n'est pas definie." >&2
  exit 1
fi

command -v curl >/dev/null 2>&1 || {
  echo "Erreur : curl est requis." >&2
  exit 1
}

command -v jq >/dev/null 2>&1 || {
  echo "Erreur : jq est requis." >&2
  exit 1
}

mkdir -p "${EXPORT_DIR}"

# Fichier temporaire pour stocker les identifiants des workflows trouves.
TMP_IDS="$(mktemp)"
trap 'rm -f "${TMP_IDS}"' EXIT

echo "API n8n      : ${N8N_API_BASE}"
echo "Tag recherche: ${DST1_TOOL_TAG}"
echo "Dossier export: ${EXPORT_DIR}"
echo

cursor=""

# Recuperation de toutes les pages de workflows actifs.
while true; do
  if [[ -n "${cursor}" ]]; then
    response="$(
      curl --silent --show-error --fail \
        --get "${N8N_API_BASE}/workflows" \
        --header "X-N8N-API-KEY: ${N8N_API_KEY}" \
        --data-urlencode "active=true" \
        --data-urlencode "cursor=${cursor}"
    )"
  else
    response="$(
      curl --silent --show-error --fail \
        --get "${N8N_API_BASE}/workflows" \
        --header "X-N8N-API-KEY: ${N8N_API_KEY}" \
        --data-urlencode "active=true"
    )"
  fi

  # Ne conserve que les workflows portant le tag dst1-tool.
  echo "${response}" | jq -r \
    --arg tag "${DST1_TOOL_TAG}" '
      .data[]
      | select(
          ([.tags[]?.name] | index($tag)) != null
        )
      | .id
    ' >> "${TMP_IDS}"

  cursor="$(echo "${response}" | jq -r '.nextCursor // empty')"

  [[ -z "${cursor}" ]] && break
done

sort -u "${TMP_IDS}" -o "${TMP_IDS}"

workflow_count="$(grep -cve '^[[:space:]]*$' "${TMP_IDS}" || true)"

if [[ "${workflow_count}" -eq 0 ]]; then
  echo "Aucun workflow actif avec le tag '${DST1_TOOL_TAG}' n'a ete trouve."
  exit 0
fi

echo "Export de ${workflow_count} workflow(s)..."
echo

exported_count=0

while IFS= read -r workflow_id; do
  [[ -z "${workflow_id}" ]] && continue

  workflow_json="$(
    curl --silent --show-error --fail \
      "${N8N_API_BASE}/workflows/${workflow_id}" \
      --header "X-N8N-API-KEY: ${N8N_API_KEY}"
  )"

  workflow_name="$(
    echo "${workflow_json}" | jq -r '.name // "workflow-sans-nom"'
  )"

  # Nom de fichier portable :
  # - minuscules ;
  # - espaces remplacés par _ ;
  # - accents et caracteres speciaux supprimes ;
  # - ID ajoute pour garantir l'unicite.
  safe_name="$(
    printf '%s' "${workflow_name}" \
      | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null \
      | tr '[:upper:]' '[:lower:]' \
      | sed -E 's/[^a-z0-9]+/_/g; s/^_+//; s/_+$//'
  )"

  [[ -z "${safe_name}" ]] && safe_name="workflow"

  output_file="${EXPORT_DIR}/${safe_name}__${workflow_id}.json"

  # Pretty-print JSON pour versioning Git / lecture humaine.
  echo "${workflow_json}" | jq '.' > "${output_file}"

  echo "OK  ${workflow_name}"
  echo "    -> ${output_file}"

  exported_count=$((exported_count + 1))
done < "${TMP_IDS}"

echo
echo "Export termine : ${exported_count} fichier(s) dans ${EXPORT_DIR}"
