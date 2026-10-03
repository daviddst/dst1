# Enregistrement Tool Diagnostic — DST1

## ✅ État : Complètement enregistré

Date : 2026-09-29

---

## 📋 Résumé de l'enregistrement

Le tool de diagnostic automatique a été enregistré comme un outil disponible dans l'agent DST1.

### Informations du tool

| Propriété | Valeur |
|-----------|--------|
| **Nom** | `analyser_logs_diagnostic` |
| **Type** | Outil interne Python (non n8n) |
| **Tag** | `dst1-diagnostic` |
| **Module** | `diagnostic_tool.py` |
| **Fonction** | `create_diagnostic_function_tool()` |
| **Déclenchement** | Automatique (ErrorEvent) + Manuel (fonction tool) |

### Description complète

```
Lance une analyse automatique des logs de l'agent des 5 dernières minutes. 
Extrait les erreurs, exclut les logs LiveKit, et retourne une synthèse 
intelligente via Gemini Flash. Aucun paramètre requis.
```

---

## 🔧 Fonctionnement technique

### Enregistrement dans le système

```
tool_loader.py
  ├─ Import : from diagnostic_tool import create_diagnostic_function_tool
  ├─ Découverte des tools n8n (15 outils)
  └─ Ajout du tool diagnostic : +1 outil interne
     └─ Total : 16 outils disponibles pour l'agent
```

### Intégration à l'agent

```
agent.py
  ├─ Charge les tools via discover_tools_from_n8n()
  ├─ Inclut le diagnostic dans la liste
  └─ Intègre au résumé des outils pour le prompt système
```

### Flux d'utilisation

**Mode automatique** (exécution automatique à chaque ErrorEvent) :
```
ErrorEvent déclenché
  └─ register_error_handler()
     └─ asyncio.create_task(run_diagnostic_on_error())
        └─ Analyse logs + synthèse Gemini
        └─ Enregistre résultat dans logs
```

**Mode manuel** (utilisateur appelle le tool via l'agent) :
```
Utilisateur: "Analyse les erreurs récentes"
  └─ Agent détecte l'intention
  └─ Appelle function_tool 'analyser_logs_diagnostic'
  └─ Retourne synthèse intelligente à l'utilisateur
```

---

## 📦 Fichiers modifiés/créés

### Modifiés

1. **`services/agent/diagnostic_tool.py`**
   - Ajout de `diagnostic_tool_handler()` — handler function_tool
   - Ajout de `create_diagnostic_function_tool()` — factory pour enregistrement
   - Ligne 51-102

2. **`services/agent/tool_loader.py`**
   - Import de `create_diagnostic_function_tool`
   - Ajout du flag `DIAGNOSTIC_TOOL_AVAILABLE`
   - Enregistrement du tool en fin de `discover_tools_from_n8n()`
   - Ligne 8-14 (imports) et ligne 328-336 (enregistrement)

### Créés

1. **`n8n/tool-catalog/diagnostic-tool.md`** — Documentation complète du tool

---

## 🎯 Vérifications de déploiement

### Logs de déploiement

```
INFO:dst1-tool-loader:Tool interne 'analyser_logs_diagnostic' (diagnostic) enregistré
```

### Test d'enregistrement

```bash
# Vérifier la présence dans le résumé des outils
docker compose exec -T dst1-agent python3 << 'PY'
import sys, asyncio
sys.path.insert(0, '/app')
from tool_loader import discover_tools_from_n8n
tools = asyncio.run(discover_tools_from_n8n())
print(f"Total: {len(tools)} outils")  # Devrait afficher 16
PY
```

**Résultat** ✅ : 16 outils (15 n8n + 1 diagnostic)

### Présence dans le résumé

```
Voici les outils actuellement a ta disposition :
- gerer_rappels_rdv : ...
- envoyer_message_whatsapp : ...
...
- analyser_logs_diagnostic : Lance une analyse automatique des logs de l'agent des 5 dernières minutes.
```

**Résultat** ✅ : Tool visible dans le contexte agent

---

## 🚀 Utilisation

### Par l'utilisateur

```
Utilisateur: "Vérifie s'il y a eu des erreurs récemment"
Agent: [Appelle analyser_logs_diagnostic]
Réponse: "Aucune erreur trouvée dans les 5 dernières minutes. ✓"
```

### Par le système (automatique)

```
[Tool échoue ou session erreur]
  └─ ErrorEvent levé
  └─ Diagnostic lancé en arrière-plan
  └─ Logs agentisés
  └─ Synthèse enregistrée dans agent.log
```

---

## 📊 Statistiques

| Métrique | Valeur |
|----------|--------|
| **Tools n8n** | 15 |
| **Tools internes** | 1 (diagnostic) |
| **Total tools** | 16 |
| **Paramètres diagnostic** | 0 (aucun requis) |
| **Déclenchements** | 2 (automatique + manuel) |
| **Fournisseur synthèse** | Gemini Flash 2.5 |

---

## ✅ Checklist de validation

- ✓ Fichier `diagnostic_tool.py` créé
- ✓ Function `create_diagnostic_function_tool()` implémentée
- ✓ Import dans `tool_loader.py` effectué
- ✓ Enregistrement dans `discover_tools_from_n8n()` ajouté
- ✓ Syntaxe Python validée
- ✓ Service redéployé
- ✓ Logs d'enregistrement confirmés
- ✓ Présence dans le résumé des outils vérifiée
- ✓ Documentation créée (`diagnostic-tool.md`)
- ✓ Test de fonctionnement réussi

---

## 🔗 Références

- **Code** : `services/agent/diagnostic_tool.py` (fonction `create_diagnostic_function_tool`)
- **Intégration** : `services/agent/tool_loader.py` (import + enregistrement)
- **Déclenchement auto** : `services/agent/agent.py` (ErrorEvent handler)
- **Catalogue** : `n8n/tool-catalog/diagnostic-tool.md`
- **Configuration** : `docker/build/dst1-agent/requirements.txt` (google-generativeai)

---

## 🎉 Conclusion

Le tool de diagnostic **est maintenant enregistré et opérationnel** en tant que :
1. **Outil interne** — Disponible dans la liste des outils de l'agent
2. **Function tool** — Appelable manuellement par l'utilisateur
3. **Outil autonome** — Exécution automatique lors des erreurs

**Total : 16 outils** disponibles pour DST1, dont le diagnostic comme outil de monitoring.
