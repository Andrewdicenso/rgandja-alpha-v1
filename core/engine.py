import sys
import logging
from pathlib import Path
from datetime import datetime

# ==============================================================================
# RISOLUZIONE DINAMICA DEL PATH PER STREAMLIT
# ==============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.secure_vault import SecureVault
from core.database import DatabaseAziendale
from core.experimental_modules.engine_settori import analizza_e_configura_motore

logger = logging.getLogger("RGD-Alpha.Gateway.Enterprise")

class DataGateway:
    """
    Gateway Enterprise: Sistema di analisi predittiva con protocollo EMA (Alpha).
    Include What-If Analysis e calcolo dinamico del Momentum finanziario.
    """
    def __init__(self):
        try:
            self.vault = SecureVault(key_path="core/security/vault.key")
            self.db = DatabaseAziendale()
        except Exception as e:
            logger.critical(f"Errore critico avvio componenti core: {e}")
            raise
        
        self.pesi_contesto = {
            "Magazzino": 1.2,
            "Fornitori": 1.5,
            "Performance Vendite": 1.0,
            "UNIVERSAL": 1.0
        }

    def _archivia_asset(self, asset, rischio_pesato):
        """Persistenza atomica sul database multi-tenant."""
        try:
            if isinstance(asset, dict):
                user_id = asset.get("user_id", 1)
                nome_asset = asset.get("nome", "Prodotto_Ignoto")
                tipo = asset.get("tipo", "GenericAsset")
                momentum = asset.get("momentum", "Stabile")
                volatilita = asset.get("volatilita", 0.0)
            else:
                user_id = getattr(asset, 'user_id', 1)
                nome_asset = getattr(asset, 'nome', 'Prodotto_Ignoto')
                tipo = getattr(asset, 'tipo', 'GenericAsset')
                momentum = getattr(asset, 'momentum', 'Stabile')
                volatilita = getattr(asset, 'volatilita', 0.0)

            self.db.salva_asset(
                user_id=user_id,
                nome_asset=nome_asset,
                rischio=rischio_pesato,
                tipo=tipo,
                momentum=momentum,
                volatilita=volatilita
            )
        except Exception as e:
            logger.warning(f"Archiviazione fallita: {e}")

    def _calcola_trend_momentum_alpha(self, rischio_oggi, rischio_storico, w1=0.7, w2=0.3, dt=1):
        """
        IMPLEMENTAZIONE FORMULA EMA (IMAGE 6):
        M = ((Roggi * W1) - (Rstorico * W2)) / dt
        """
        if dt <= 0: dt = 1
        momentum_score = ((rischio_oggi * w1) - (rischio_storico * w2)) / dt
        return round(momentum_score, 2)

    def _genera_consiglio_azione(self, rischio, settore, momentum_score=0):
        """Genera un consiglio pratico basato su rischio, settore e accelerazione."""
        alert_text = " ⚠️ ACCELERAZIONE CRITICA!" if momentum_score > 1.5 else ""

        if rischio > 8:
            if settore == "LOGISTICS":
                return f"🚨 CRITICO: Avviare liquidazione immediata per liberare spazio.{alert_text}"
            if settore == "FINANCE":
                return f"🚨 CRITICO: Rischio svalutazione totale asset. Revisione contratti.{alert_text}"
            return f"🚨 CRITICO: Azione d'emergenza richiesta entro 48 ore.{alert_text}"
        
        elif rischio > 5:
            if settore == "LOGISTICS":
                return f"⚠️ ATTENZIONE: Pianificare promozione 'Bundle' per aumentare rotazione.{alert_text}"
            return f"⚠️ ATTENZIONE: Monitoraggio intensivo richiesto per i prossimi 7 giorni.{alert_text}"
        
        else:
            return "✅ OTTIMALE: Parametri stabili. Proseguire con ordinaria amministrazione."

    def esegui_scan_strategico(self, lista_asset, contesto, fattore_stress=1.0, weights=(0.7, 0.3)):
        """
        Analisi Avanzata RGD-ALPHA con WHAT-IF e TREND MOMENTUM.
        Passa il parametro weights=(w1, w2) per calibrare l'EMA dall'interfaccia.
        """
        colonne = []
        if lista_asset:
            primo_asset = lista_asset[0]
            colonne = list(primo_asset.keys()) if isinstance(primo_asset, dict) else list(vars(primo_asset).keys())
        
        config_settore = analizza_e_configura_motore(colonne)
        settore_rilevato = config_settore.get("settore", "GENERAL")
        soglia_critica = config_settore.get("soglia", 7.0)
        
        moltiplicatore_finale = config_settore.get("moltiplicatore", 1.0) * self.pesi_contesto.get(contesto, 1.0) * fattore_stress
        
        w1, w2 = weights
        report = []
        
        for asset in lista_asset:
            nome_asset = asset.get("nome", "Prodotto") if isinstance(asset, dict) else getattr(asset, 'nome', 'Prodotto')
            rischio_base = asset.get("rischio", 0.0) if isinstance(asset, dict) else getattr(asset, 'rischio', 0.0)
            
            # Calcolo Rischio Pesato con Stress Test
            rischio_pesato = round(rischio_base * moltiplicatore_finale, 2)
            
            # Recupero rischio storico simulato (per il test) o dal DB
            rischio_storico = rischio_base * 0.85 # Simulazione trend in crescita
            
            # Calcolo Momentum EMA
            m_score = self._calcola_trend_momentum_alpha(rischio_pesato, rischio_storico, w1=w1, w2=w2)
            
            # Generazione Consiglio IA
            consiglio = self._genera_consiglio_azione(rischio_pesato, settore_rilevato, m_score)
            
            # Definizione stato visivo
            stato_salute = "CRITICO" if rischio_pesato > soglia_critica else "OTTIMALE"
            if 5.0 < rischio_pesato <= soglia_critica:
                stato_salute = "ATTENZIONE"

            report.append({
                "asset": nome_asset,
                "stato": stato_salute,
                "rischio": rischio_pesato,
                "momentum_score": m_score,
                "consiglio_strategico": consiglio,
                "settore": settore_rilevato,
                "alert": "🚨 STRESS TEST ATTIVO" if fattore_stress > 1.0 else "Parametri nominali"
            })
            
            # Archiviazione storica per calcoli futuri
            self._archivia_asset(asset, rischio_pesato)
            
        return report

def salva_report_certificato(azienda, dati_report, vault):
    """Genera un blob cifrato per la notarizzazione del report."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        certificato = f"TS: {timestamp} | AZIENDA: {azienda} | PROTOCOLLO ALPHA CERTIFIED | AES-256"
        return vault.encrypt_data(certificato)
    except:
        return None