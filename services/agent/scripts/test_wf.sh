curl -v -X POST http://localhost:5678/webhook/dst1-creer-workflow-outil \
  -H "Content-Type: application/json" \
  -d '{
    "nom_outil": "test_debug",
    "description_fonctionnelle": "Outil de test pour deboguer le workflow meta"
  }'
