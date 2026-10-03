# Outil de Diagnostic Automatique — DST1

## 📋 Résumé du déploiement

Un nouvel outil de diagnostic a été créé et déployé automatiquement. Il analyse les logs d'erreur du service `dst1-agent` et les synthétise via **Gemini Flash 2.5**.

---

## 🎯 Fonctionnalités

### Analyseur de logs
- Scanne `/app/logs/agent.log` des **5 dernières minutes**
- Extrait les erreurs (`| ERROR |`) et avertissements (`| WARNING |`)
- **Exclut automatiquement** les logs `WARNING:livekit`
- Résultat : liste d'erreurs structurée avec timestamps

### Synthèse Gemini Flash
- Envoie les erreurs trouvées à l'API Google Generative AI
- Modèle utilisé : `gemini-2.5-flash`
- Retourne une synthèse en **5-10 points clés** en français
- Identifie les patterns récurrents et les sévérités

### Déclenchement automatique
Le diagnostic s'exécute automatiquement quand :
- Un **ErrorEvent** est levé dans une session agent (tool failure, session crash, etc.)
- Exécution asynchrone en arrière-plan (non-bloquant)
- Résultat enregistré dans les logs : `DIAGNOSTIC: X erreurs en [timestamp] | Synthese: ...`

---

## 📁 Fichiers créés/modifiés

| Fichier | Changement |
|---------|-----------|
| `services/agent/diagnostic_tool.py` | **Créé** — Outil principal |
| `services/agent/agent.py` | Modifié — Import + appel auto du diagnostic |
| `docker/build/dst1-agent/requirements.txt` | Modifié — `google-genai` → `google-generativeai` |

---

## 🔧 Configuration requise

Pour fonctionner en mode complet, l'env var suivante doit être définie dans le conteneur :

```bash
GOOGLE_API_KEY=your-api-key-here
```

**Mode dégradé** : Si la clé n'est pas présente, le diagnostic :
- Continue à extraire les erreurs brutes
- Retourne juste la liste sans synthèse Gemini
- Log un warning : `"google-generativeai non disponible, diagnostique en mode degrade"`

---

## 📊 Exemple d'exécution

### Input (Logs bruts)
```
2026-09-29 20:54:56 | ERROR | tool_executor | Timeout lors de l'appel webhook dst1-envoyer-email
2026-09-29 20:54:57 | WARNING | dst1-agent | Retentative #1 en cours...
2026-09-29 20:55:00 | ERROR | tool_executor | Webhook response empty
```

### Output (Diagnostic complet)
```json
{
  "timestamp": "2026-09-29T20:55:02.123456+00:00",
  "errors_count": 3,
  "raw_errors": [
    "2026-09-29 20:54:56 | ERROR | tool_executor | Timeout lors de l'appel webhook dst1-envoyer-email",
    "2026-09-29 20:54:57 | WARNING | dst1-agent | Retentative #1 en cours...",
    "2026-09-29 20:55:00 | ERROR | tool_executor | Webhook response empty"
  ],
  "synthesis": "• Webhook dst1-envoyer-email subit des timeouts répétés\n• Pattern: timeout suivi de réponse vide (possibilité de crash backend)\n• Recommandation: vérifier la santé du service dst1-n8n et les timeouts réseau"
}
```

---

## 🧪 Test local

Pour tester manuellement :

```bash
# Dans le conteneur
docker compose exec -T dst1-agent python3 << 'PY'
import sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '/app')
from diagnostic_tool import DiagnosticTool

# Créer des logs de test
now = datetime.now(timezone.utc)
with open('/tmp/test.log', 'w') as f:
    f.write(f"{(now - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')} | ERROR | test | Erreur test\n")
    f.write(f"{(now - timedelta(minutes=3)).strftime('%Y-%m-%d %H:%M:%S')} | WARNING | livekit.foo | Warning livekit (exclu)\n")

# Tester
diag = DiagnosticTool(log_file="/tmp/test.log")
errors = diag.get_recent_errors(minutes=5)
print(f"Erreurs trouvées: {len(errors)}")
PY
```

---

## 📝 Architecture

```
┌─────────────────────────────────────┐
│  LiveKit Agent Session              │
│  (dst1-agent)                       │
└──────────────┬──────────────────────┘
               │
               ├─► Tool Execution
               │   ↓
               ├─► ErrorEvent raised
               │   ↓
               └─► register_error_handler()
                   ├─► Session recovery (say error message)
                   │
                   └─► asyncio.create_task(run_diagnostic_on_error())
                       │
                       └─► DiagnosticTool.run_diagnostic()
                           ├─► Read /app/logs/agent.log (last 5 min)
                           ├─► Filter: ERROR | WARNING (exclude livekit)
                           ├─► Send to Gemini Flash 2.5 (if API key present)
                           └─► Log summary in agent.log
```

---

## ⚙️ Variables d'environnement

| Variable | Valeur | Source |
|----------|--------|--------|
| `GOOGLE_API_KEY` | API key Gemini | À configurer dans le `.env` |
| `N8N_WEBHOOK_BASE` | `http://dst1-n8n:5678/webhook` | `agent_config.yaml` |
| `N8N_API_BASE` | `http://dst1-n8n:5678/api/v1` | `agent_config.yaml` |

---

## 🚀 Commandes utiles

```bash
# Voir les logs du diagnostic
make logs SERVICE=dst1-agent 2>&1 | grep DIAGNOSTIC

# Redéployer si modifications
make deploy-agent

# Reconstruire l'image (si requirements.txt change)
cd /etc/docker && docker compose build --no-cache dst1-agent

# Health check
docker compose exec -T dst1-agent python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health')"
```

---

## ✅ État du déploiement

- ✓ Fichier `diagnostic_tool.py` synchronisé
- ✓ Import dans `agent.py` intégré
- ✓ Dépendances installées (`google-generativeai`)
- ✓ Service redémarré et sain
- ✓ Health check réussi
- ✓ Test de filtrage log réussi (livekit exclu)

**Prêt pour la production !**
