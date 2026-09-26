# Emplacement : a executer dans la base dst1_agent
# (via psql, ou ajouter comme 02-schema-workflow-audit.sql dans
#  /etc/docker/build/dst1-postgres/init/ pour les futurs deploiements)
#
# Usage manuel :
#   docker exec -i dst1-postgres psql -U dst1_admin -d dst1_agent < init-workflow-audit.sql

\c dst1_agent

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Historique complet de toutes les creations/modifications/corrections
-- de workflows n8n effectuees par l'outil meta-workflow de DST1.
-- payload_avant / payload_apres contiennent le JSON complet du workflow,
-- ce qui permet un rollback manuel en cas de probleme.
CREATE TABLE IF NOT EXISTS workflow_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'fix')),
    workflow_id TEXT,
    workflow_name TEXT,
    payload_avant JSONB,
    payload_apres JSONB,
    resultat TEXT NOT NULL CHECK (resultat IN ('succes', 'echec')),
    erreur TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflow_audit_workflow_id
    ON workflow_audit_log(workflow_id);

CREATE INDEX IF NOT EXISTS idx_workflow_audit_created_at
    ON workflow_audit_log(created_at DESC);

SELECT 'Table workflow_audit_log initialisee avec succes.' AS status;

