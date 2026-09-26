\c dst1_agent

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Rendez-vous
CREATE TABLE IF NOT EXISTS rdv (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titre TEXT NOT NULL,
    description TEXT,
    date_debut TIMESTAMPTZ NOT NULL,
    date_fin TIMESTAMPTZ,
    lieu TEXT,
    statut TEXT DEFAULT 'planifié',
    google_event_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Tâches
CREATE TABLE IF NOT EXISTS taches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titre TEXT NOT NULL,
    description TEXT,
    priorite SMALLINT DEFAULT 3,
    statut TEXT DEFAULT 'a_faire',
    echeance TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Périphériques domotique
CREATE TABLE IF NOT EXISTS domotique_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom TEXT NOT NULL,
    type TEXT,
    entity_id_ha TEXT UNIQUE NOT NULL,
    etat JSONB,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Journal des interactions
CREATE TABLE IF NOT EXISTS conversation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT,
    role TEXT CHECK (role IN ('user','agent','system')),
    contenu TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Mémoire vectorielle (RAG mails, notes, contexte long terme)
-- dimension 768 = text-embedding-004 (Google)
CREATE TABLE IF NOT EXISTS memoire_vectorielle (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT,
    reference_id TEXT,
    contenu TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memoire_embedding
    ON memoire_vectorielle
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
