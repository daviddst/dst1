# Inventaire DST1

## Sources a copier manuellement

- /etc/docker/docker-compose.yml
- /volume/dst1-agent/agent.py
- /volume/dst1-agent/agent_config.yaml
- /volume/dst1-agent/tool_loader.py
- /volume/dst1-agent/text_endpoint.py
- /volume/dst1-web/server.py
- /volume/dst1-web/static/index.html

## Sources a auditer avant copie

- /etc/docker/build

## Ne jamais copier directement

- /volume/dst1-n8n
- /volume/dst1-postgres
- /volume/dst1-logs
- /volume/evolution-postgres
- /volume/whatsapp-redis

Ces emplacements contiennent de l etat runtime, des credentials, des logs,
des donnees de bases, des caches ou des donnees potentiellement sensibles.
