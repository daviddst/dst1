docker compose -f /etc/docker/docker-compose.yml --env-file /etc/docker/.env exec dst1-postgres psql -U dst1_admin -d n8n -c \
  "SELECT * FROM webhook_entity ;"
#  "SELECT \"webhookPath\", method, \"workflowId\" FROM webhook_entity WHERE \"webhookPath\" LIKE '%';"
