# diagnostic_tool.py
# Outil automatique de diagnostic des erreurs — analyse les logs dst1-agent
# et synthetise les problemes via Gemini Flash.

import os
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List

logger = logging.getLogger("diagnostic_tool")

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai non disponible, diagnostique en mode degrade")


class DiagnosticTool:
    """Analyse les logs d'erreur et synthetise via Gemini Flash."""

    def __init__(self, log_file: str = "/app/logs/agent.log"):
        self.log_file = log_file
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        
        if GENAI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")
        else:
            self.model = None

    def get_recent_errors(self, minutes: int = 5) -> List[str]:
        """
        Extrait les erreurs/warnings des N dernieres minutes du fichier log.
        Exclut les logs WARNING:livekit.
        
        Format attendu : YYYY-MM-DD HH:MM:SS | LEVEL | logger_name | message
        """
        if not os.path.exists(self.log_file):
            logger.warning(f"Fichier log {self.log_file} introuvable")
            return []

        errors = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    # Ignorer les logs livekit
                    if "WARNING:livekit" in line or "| livekit." in line:
                        continue
                    
                    # Chercher les erreurs et warnings (sauf livekit)
                    if "| ERROR |" in line or "| WARNING |" in line:
                        # Parser le timestamp
                        try:
                            # Format : 2026-09-29 15:30:45
                            ts_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                            if ts_match:
                                ts_str = ts_match.group(1)
                                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                                # Ajouter TZ UTC pour la comparaison
                                ts = ts.replace(tzinfo=timezone.utc)
                                
                                if ts >= cutoff_time:
                                    errors.append(line.strip())
                        except Exception as e:
                            logger.debug(f"Erreur parsing timestamp : {e}")
                            # Par defaut inclure si on ne peut pas parser
                            if "| ERROR |" in line or "| WARNING |" in line:
                                errors.append(line.strip())
        except Exception as e:
            logger.error(f"Erreur lecture log {self.log_file}: {e}")

        return errors

    async def synthesize_with_gemini(self, errors: List[str]) -> Optional[str]:
        """
        Envoie les erreurs a Gemini Flash pour une synthese.
        """
        if not self.model:
            logger.warning("Gemini non configure, synthese impossible")
            return None

        if not errors:
            return "✓ Aucune erreur trouvée dans les 5 dernières minutes."

        errors_text = "\n".join(errors)
        prompt = f"""Synthetise ces erreurs/warnings d'un agent assistant vocal en ~5-10 points clés.
Identifie les patterns recurrents et les severites.
Format : bullet points directs, français.

ERREURS/WARNINGS :
{errors_text}

SYNTHESE :"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Erreur appel Gemini : {e}")
            return None

    async def run_diagnostic(self, minutes: int = 5) -> Dict[str, any]:
        """
        Lance le diagnostique complet.
        Retourne : {
            "timestamp": str,
            "errors_count": int,
            "raw_errors": List[str],
            "synthesis": str (jamais None)
        }
        """
        errors = self.get_recent_errors(minutes)
        synthesis = None
        
        if errors and self.model:
            synthesis = await self.synthesize_with_gemini(errors)
        elif errors:
            # Si pas de Gemini, retourner juste les erreurs
            synthesis = "Synthese Gemini non disponible. Erreurs brutes :\n" + "\n".join(errors[:10])

        # Fallback si synthesis est None (erreur Gemini ou pas d'erreurs)
        if synthesis is None:
            if errors:
                synthesis = f"Erreurs détectées ({len(errors)}) mais synthèse Gemini indisponible. Consulter les logs bruts."
            else:
                synthesis = "✓ Aucune erreur trouvée dans les 5 dernières minutes."

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "errors_count": len(errors),
            "raw_errors": errors[:20],  # Limiter a 20 pour la taille
            "synthesis": synthesis,
        }

        logger.info(f"Diagnostique complet : {len(errors)} erreurs trouvees")
        return result

    def log_diagnostic(self, diagnostic: Dict) -> None:
        """Enregistre le resultat du diagnostique dans les logs."""
        synthesis = diagnostic.get('synthesis') or 'N/A'
        logger.warning(
            f"DIAGNOSTIC: {diagnostic['errors_count']} erreurs en {diagnostic['timestamp']} | "
            f"Synthese: {synthesis[:200]}"
        )


async def run_diagnostic_on_error(error_msg: Optional[str] = None) -> Dict:
    """
    Fonction publique pour lancer un diagnostique automatique.
    Appelee lors d'une ErrorEvent.
    """
    diagnostic = DiagnosticTool()
    result = await diagnostic.run_diagnostic(minutes=5)
    
    if error_msg:
        result["error_trigger"] = error_msg
    
    diagnostic.log_diagnostic(result)
    return result


async def diagnostic_tool_handler(params: Optional[Dict] = None, context=None) -> Dict[str, any]:
    """
    Handler function_tool pour exposer le diagnostic comme un outil utilisable.
    Tag : dst1-diagnostic (outil interne de monitoring)
    
    Aucun paramètre requis : lance un diagnostique complet des 5 dernières minutes.
    """
    result = await run_diagnostic_on_error(error_msg="Lancé manuellement via tool call")
    
    # Formater la réponse pour l'agent
    return {
        "status": "success",
        "errors_found": result["errors_count"],
        "synthesis": result.get("synthesis") or "Aucun diagnostic disponible",
        "timestamp": result["timestamp"],
    }


def create_diagnostic_function_tool():
    """
    Crée et retourne une function_tool enregistrée pour le diagnostic.
    À appeler depuis tool_loader.py pour ajouter le diagnostic aux outils disponibles.
    """
    try:
        from livekit.agents import function_tool
    except ImportError:
        logger.error("LiveKit agents non disponible, diagnostic tool non enregistré")
        return None
    
    raw_schema = {
        "type": "function",
        "name": "analyser_logs_diagnostic",
        "description": (
            "Lance une analyse automatique des logs de l'agent des 5 dernières minutes. "
            "Extrait les erreurs, exclut les logs LiveKit, et retourne une synthèse "
            "intelligente via Gemini Flash. Aucun paramètre requis."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }
    
    tool = function_tool(diagnostic_tool_handler, raw_schema=raw_schema)
    logger.info("Tool diagnostic enregistré avec tag 'dst1-diagnostic'")
    return tool
