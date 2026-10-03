# consulter_agenda
curl -s -X POST http://localhost:5678/webhook/dst1-consulter-agenda \
  -H "Content-Type: application/json" \
  -d '{"periode":"aujourd_hui"}'

# create_rdv
curl -s -X POST http://localhost:5678/webhook/dst1-create-rdv \
  -H "Content-Type: application/json" \
  -d "{\"titre\":\"Test curl\",\"date_debut\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
