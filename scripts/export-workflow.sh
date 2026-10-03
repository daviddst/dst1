#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKFLOW_ID="${1:-}"

if [[ ! "${WORKFLOW_ID}" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "Usage: N8N_API_BASE=... N8N_API_KEY=... bash scripts/export-workflow.sh <workflow_id>" >&2
  exit 2
fi
if [[ -z "${N8N_API_BASE:-}" || -z "${N8N_API_KEY:-}" ]]; then
  echo "Erreur : définir N8N_API_BASE et N8N_API_KEY dans l’environnement." >&2
  exit 2
fi

workflow_json="$(curl --silent --show-error --fail \
  "${N8N_API_BASE%/}/workflows/${WORKFLOW_ID}" \
  --header "X-N8N-API-KEY: ${N8N_API_KEY}")"
workflow_name="$(jq -r '.name // "workflow-sans-nom"' <<< "${workflow_json}")"

output_file=""
for category in DST1 WFBuilder; do
  while IFS= read -r candidate; do
    candidate_id="$(jq -r '.id // empty' "${candidate}")"
    candidate_name="$(jq -r '.name // empty' "${candidate}")"
    if [[ "${candidate_id}" == "${WORKFLOW_ID}" || "${candidate_name}" == "${workflow_name}" ]]; then
      if [[ -n "${output_file}" ]]; then
        echo "Erreur : plusieurs snapshots locaux correspondent à ${workflow_name}." >&2
        exit 1
      fi
      output_file="${candidate}"
    fi
  done < <(find "${ROOT_DIR}/n8n/workflows/${category}" -type f -name '*.json' -print | sort)
done

if [[ -z "${output_file}" ]]; then
  is_dst1_tool="$(jq -r 'any(.tags[]?; .name == "dst1-tool")' <<< "${workflow_json}")"
  if [[ "${is_dst1_tool}" == "true" ]]; then
    category="DST1"
  else
    category="WFBuilder"
  fi

  safe_name="$(printf '%s' "${workflow_name}" \
    | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/_/g; s/^_+//; s/_+$//')"
  [[ -n "${safe_name}" ]] || safe_name="workflow"
  output_file="${ROOT_DIR}/n8n/workflows/${category}/${safe_name}__${WORKFLOW_ID}.json"
fi

# Keep only the workflow snapshot fields; n8n does not return credential secrets.
jq '{name, nodes, connections, active, settings, id, tags}' <<< "${workflow_json}" > "${output_file}"
echo "Exporté ${workflow_name} vers ${output_file#"${ROOT_DIR}/"}"