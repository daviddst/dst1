message=$1

if [ -z "$message" ]; then
  echo "Erreur de syntaxe"
  echo "Ex: $0 'liste tes outils disponibles'"
  exit 1
fi

curl -s -X POST http://localhost:8080/text-query \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"$message\"}" \
  | python3 -m json.tool | jq "."
