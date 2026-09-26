curl -s -X POST http://localhost:5678/webhook/dst1-supprimer-rdv \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "2aldgp11c7icn4si3o47n0ae0o",
    "calendar_id": "david@xinus.net"
  }'
