curl -s -X POST http://localhost:5678/webhook/dst1-create-rdv \
  -H "Content-Type: application/json" \
  -d '{"titre":"Test 404","date_debut":"2026-09-22T10:00:00"}'
