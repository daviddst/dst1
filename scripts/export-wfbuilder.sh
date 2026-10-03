#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${WFBUILDER_PROJECT_DIR:-/srv/WFBuilder}"
EXPORT_SCRIPT="${PROJECT_DIR}/scripts/export-wfbuilder.sh"

if [[ ! -x "${EXPORT_SCRIPT}" ]]; then
  echo "Erreur : script autonome introuvable : ${EXPORT_SCRIPT}" >&2
  exit 2
fi

exec "${EXPORT_SCRIPT}" "$@"