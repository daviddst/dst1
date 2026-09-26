# 1. Lister les calendriers (déjà OK)
curl -s -X POST http://localhost:5678/webhook/dst1-lister-calendriers | head -c 300
echo ""

# 2. Consulter l'agenda
curl -s -X POST http://localhost:5678/webhook/dst1-consulter-agenda \
  -H "Content-Type: application/json" -d '{"periode":"aujourd_hui"}' | head -c 300
echo ""

# 3. Créer un RDV test
curl -s -X POST http://localhost:5678/webhook/dst1-create-rdv \
  -H "Content-Type: application/json" \
  -d '{"titre":"Test validation pipeline","date_debut":"2026-09-22T09:00:00"}' | head -c 300
echo ""
