# DST1 - Digital Smart Technician One

Depot source et documentation de DST1.

## Composants

- Agent Python LiveKit et Gemini
- Facade Web FastAPI
- n8n pour workflows et outils
- PostgreSQL avec pgvector
- Evolution API et WhatsApp
- Redis
- Whisper

## Ce qui est versionne

- Sources applicatives
- Docker Compose et Dockerfiles apres audit
- Configurations non secretes
- Documentation et scripts
- Exports JSON n8n nettoyes

## Ce qui est exclu

- Fichiers env reels
- Mots de passe, tokens et cles API
- Volumes Docker
- Bases de donnees
- Credentials et executions n8n
- Logs, caches, sauvegardes et conversations

## Demarrage

Lancer les commandes suivantes :

    cd /Users/david/Projets/DST1
    make checklist
    make validate
    git status

Les fichiers avec extension A_COPIER sont une checklist de copie manuelle
depuis le serveur. Aucun fichier serveur n est copie automatiquement.
