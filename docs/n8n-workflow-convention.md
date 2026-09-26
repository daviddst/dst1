# Conventions n8n DST1

Les workflows versionnes sont places dans n8n/workflows au format JSON.

Ne jamais exporter dans Git :

- credentials
- tokens
- cles
- executions
- donnees personnelles
- contenu du volume n8n

## Convention outils DST1

Un workflow decouvert comme outil doit :

1. etre actif
2. porter le tag dst1-tool
3. comporter un noeud Webhook
4. comporter un noeud aval dont le nom commence par ToolSchema
5. definir tool_name, tool_description, tool_parameters et require_confirmation

Documenter chaque outil dans n8n/tool-catalog.
