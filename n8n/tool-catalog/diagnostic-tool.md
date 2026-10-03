# Diagnostic d'erreurs automatique

## Référence

- **Type :** Outil interne Python (agent.py)
- **Module :** `diagnostic_tool.py`
- **Fonction :** `run_diagnostic_on_error()`
- **Tag :** `dst1-diagnostic` (interne, non utilisateur)
- **Déclenchement :** Automatique lors d'un ErrorEvent

## Objectif

Analyser automatiquement les logs d'erreur du service `dst1-agent` et en produire une synthèse lisible via Gemini Flash. Aucune action utilisateur n'est requise.

## Fonctionnement

### Flux automatique

```
ErrorEvent (tool failure, session crash...)
    ↓
register_error_handler() activé
    ├─ Session recovery : message utilisateur + new task
    │
    └─ asyncio.create_task(run_diagnostic_on_error())
       ├─ Extrait logs /app/logs/agent.log (5 dernières minutes)
       ├─ Filtre : | ERROR | et | WARNING | (exclut WARNING:livekit)
       ├─ Envoie à Gemini Flash 2.5 pour synthèse
       └─ Enregistre résultat dans les logs
```

### Sortie

Structure de résultat :

```json
{
  "timestamp": "2026-09-29T20:55:02.123456+00:00",
  "errors_count": 3,
  "raw_errors": [
    "2026-09-29 20:54:56 | ERROR | ...",
    "2026-09-29 20:54:57 | WARNING | ...",
    ...
  ],
  "synthesis": "• Webhook timeout répété\n• Pattern: timeout → réponse vide\n• Recommandation: vérifier la santé du backend n8n"
}
```

## Exclusions

Les logs suivants sont **systématiquement ignorés** :
- `WARNING:livekit` (tous les avertissements LiveKit SDK)
- Logs antérieurs à 5 minutes

Seuls les logs avec timestamps des 5 dernières minutes sont traités.

## Configuration

### Synthèse Gemini (optionnel)

Pour activer la synthèse via Gemini Flash 2.5, définir la variable d'environnement :

```bash
GOOGLE_API_KEY=<votre-clé-api-google>
```

**Mode dégradé** : Si la clé n'est pas présente, le diagnostic retourne juste les erreurs brutes sans synthèse. Un warning est enregistré : `"google-generativeai non disponible, diagnostique en mode degrade"`.

### Logs

Tous les résultats du diagnostic sont enregistrés dans `/app/logs/agent.log` avec un préfixe `DIAGNOSTIC:` au niveau WARNING :

```
2026-09-29 20:55:02 | WARNING | diagnostic_tool | DIAGNOSTIC: 3 erreurs en 2026-09-29T20:55:02.123456+00:00 | Synthese: • Webhook timeout répété...
```

## Cas d'usage

### Cas 1 : Tool webhook échoue
```
[Agent appelle webhook dst1-envoyer-email]
  → Timeout après 15s
  → ErrorEvent déclenche register_error_handler()
  → Diagnostic analyse les 5 dernières minutes
  → Synthèse : "Webhook dst1-envoyer-email subit des timeouts répétés"
```

### Cas 2 : Session crash
```
[Session agent crashe]
  → ErrorEvent non-récupérable
  → Diagnostic captures les logs des 5 dernières minutes
  → Synthèse : "Pattern de fuite mémoire détecté (erreurs croissantes)"
```

### Cas 3 : Mode dégradé (pas d'API key)
```
[GOOGLE_API_KEY non définie]
  → Diagnostic fonctionne mais sans synthèse
  → Retourne : erreurs brutes + warning dans les logs
```

## Fichiers associés

| Fichier | Rôle |
|---------|------|
| `services/agent/diagnostic_tool.py` | Logique d'extraction et synthèse |
| `services/agent/agent.py` | Intégration avec ErrorEvent handler |
| `docker/build/dst1-agent/requirements.txt` | Dépendance `google-generativeai` |

## Commandes utiles

### Voir les diagnostiques en temps réel
```bash
make logs SERVICE=dst1-agent 2>&1 | grep DIAGNOSTIC
```

### Tester manuellement
```bash
docker compose exec -T dst1-agent python3 << 'PY'
import sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '/app')
from diagnostic_tool import DiagnosticTool

# Créer des logs de test
now = datetime.now(timezone.utc)
with open('/tmp/test.log', 'w') as f:
    f.write(f"{(now - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')} | ERROR | test | Erreur test\n")

diag = DiagnosticTool(log_file="/tmp/test.log")
errors = diag.get_recent_errors(minutes=5)
print(f"Erreurs trouvées: {len(errors)}")
PY
```

### Health check
```bash
docker compose exec -T dst1-agent python3 -c "from diagnostic_tool import DiagnosticTool; print('✓ Module OK')"
```

## Notes opérationnelles

- **Non-bloquant** : Le diagnostic s'exécute en arrière-plan via `asyncio.create_task()`
- **Tolérant aux erreurs** : Les exceptions lors de la synthèse ne cassent pas la session
- **Logs préservés** : Les logs source ne sont jamais modifiés ou purgés par le diagnostic
- **Stateless** : Chaque diagnostic est indépendant, pas d'état persistant
- **Scalable** : Conçu pour un seul conteneur agent

## Monitoring

Pour surveiller la santé du diagnostic :

1. **Vérifier les warnings dans les logs agent** :
   ```bash
   make logs SERVICE=dst1-agent 2>&1 | grep "diagnostic\|DIAGNOSTIC"
   ```

2. **Compter les erreurs détectées** :
   ```bash
   make logs SERVICE=dst1-agent 2>&1 | grep "DIAGNOSTIC:" | wc -l
   ```

3. **Analyser les patterns** :
   ```bash
   make logs SERVICE=dst1-agent 2>&1 | grep "DIAGNOSTIC:" | tail -10
   ```

## Versions

| Version | Date | Changements |
|---------|------|-------------|
| 1.0 | 2026-09-29 | Version initiale — analyse logs + synthèse Gemini Flash 2.5 |

---

**État** : ✅ Production-ready  
**Maintenance** : Aucune intervention manuelle requise  
**Support** : Pour les erreurs, consulter `/app/logs/agent.log`
