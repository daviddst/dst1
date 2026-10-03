curl -s -X POST http://localhost:5678/webhook/dst1-create-rdv \
  -H "Content-Type: application/json" \
  -d "{\"titre\":\"Test 404\",\"date_debut\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
