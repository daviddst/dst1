# Runbook DST1

## Avant modification

    cd /Users/david/Projets/DST1
    git status
    make validate

## Apres synchronisation serveur explicitement validee

Pour modifier agent.py, tool_loader.py, text_endpoint.py ou agent_config.yaml :

    cd /etc/docker
    docker compose restart dst1-agent

Pour modifier server.py :

    cd /etc/docker
    docker compose restart dst1-web

Une modification de fichier statique Web peut seulement necessiter un
rechargement navigateur.

## Interdit sans plan, sauvegarde et validation

    docker compose down
    docker system prune
    docker volume prune
