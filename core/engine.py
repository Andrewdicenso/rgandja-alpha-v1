# FILE: core/engine.py
import sys
import logging
from pathlib import Path
from datetime import datetime

# ==============================================================================
# RISOLUZIONE DINAMICA DEL PATH PER STREAMLIT (Evita ModuleNotFoundError)
# ==============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.secure_vault import SecureVault
from core.database import DatabaseAziendale
from core.engine_settori import analizza_e_configura_motore

# Configurazione logging avanzato per Audit Aziendale
logger = logging.getLogger("RGD-Alpha.Gateway.Enterprise")

class DataGateway:
    """
    Gateway Enterprise: Sistema di analisi, protezione e simulazione predittiva.
    Gestisce il flusso dati tra l'ingestione e l'archiviazione storica.
    """
    def __init__(self):
        try:
            # Percorso centralizzato: garantisce l'avvio indipendentemente dal punto di esecuzione
            self.vault = SecureVault(key_path="core/security/vault.key")
            self.db = DatabaseAziendale()
        except Exception as e:
            logger.critical(f"Errore critico avvio componenti core: {e}")
            raise
        
        # Pesi strategici: riflettono la sensibilità del business
        self.pesi_contesto = {
            "Magazzino": 1.2,
            "Fornitori": 1.5,
            "Performance Vendite": 1.0,
            "UNIVERSAL": 1.0  # Allineamento con la Dashboard principale
        }

    def _archivia_asset(self, asset, rischio_pesato):
        """Salvataggio nel DB adattivo per supportare sia Oggetti che Dizionari."""
        try:
            # Riconoscimento robusto della tipologia di struttura dati passata
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

            # Esecuzione persistenza atomica sul database allineata con il modulo aziendale
            self.db.salva_asset(
                user_id=user_id,
                nome_asset=nome_asset,
                rischio=rischio_pesato,
                tipo=tipo,
                momentum=momentum,
                volatilita=volatilita
            )
        except Exception as e:
            # Evitiamo crash critici se un singolo asset è corrotto durante lo storicizzazione
            nome_log = asset.get('nome', '?') if isinstance(asset, dict) else getattr(asset, 'nome', '?')
            logger.warning(f"Archiviazione fallita per asset {nome_log}: {e}")

    def esegui_scan_strategico(self, lista_asset, contesto):
        """
        Analisi Avanzata RGD-ALPHA: Integra il riconoscimento automatico del settore
        con proiezioni predittive a 30 e 90 giorni supportando input ibridi.
        """
        colonne = []
        if lista_asset:
            primo_asset = lista_asset[0]
            # Estrazione sicura delle chiavi a seconda del formato (Dizionario o Oggetto)
            if isinstance(primo_asset, dict):
                colonne = list(primo_asset.keys())
                if "dati_extra" in primo_asset and isinstance(primo_asset["dati_extra"], dict):
                    colonne.extend(primo_asset["dati_extra"].keys())
            else:
                colonne = list(vars(primo_asset).keys())
                if hasattr(primo_asset, 'dati_extra') and isinstance(primo_asset.dati_extra, dict):
                    colonne.extend(primo_asset.dati_extra.keys())
        
        # --- LOG DI DIAGNOSI PER IL TERMINALE ---
        print("\n" + "="*50)
        print(f"🔍 [DIAGNOSI RGD-ALPHA] Asset analizzati: {len(lista_asset)}")
        print(f"📋 Tutte le chiavi rilevate (incluse extra): {colonne}")
        if lista_asset:
            sample = lista_asset[0]
            extra_sample = sample.get('dati_extra', {}) if isinstance(sample, dict) else getattr(sample, 'dati_extra', {})
            print(f"📄 Esempio dati extra primo asset: {extra_sample}")
        print("="*50 + "\n")
        
        config_settore = analizza_e_configura_motore(colonne)
        
        # Parametri dinamici estrapolati dal modulo settori
        soglia_critica = config_settore["soglia"]
        moltiplicatore_settore = config_settore["moltiplicatore"]
        moltiplicatore_contesto = self.pesi_contesto.get(contesto, 1.0)
        
        moltiplicatore_finale = moltiplicatore_settore * moltiplicatore_contesto
        
        report = []
        for asset in lista_asset:
            # Estrazione valori adattiva
            if isinstance(asset, dict):
                nome_asset = asset.get("nome", "Prodotto")
                rischio_base = asset.get("rischio", 0.0)
            else:
                nome_asset = getattr(asset, 'nome', 'Prodotto')
                rischio_base = getattr(asset, 'rischio', 0.0)
                
            rischio_pesato = round(rischio_base * moltiplicatore_finale, 2)
            
            # --- ALIMENTAZIONE DATABASE ---
            self._archivia_asset(asset, rischio_pesato)
            
            # --- MOTORE PREDITTIVO AUTOMATICO ---
            proiezione_30gg = round(rischio_pesato * 1.25, 2)
            proiezione_90gg = round(rischio_pesato * 1.5, 2)
            
            dettagli_alert = []
            if rischio_pesato > soglia_critica:
                dettagli_alert.append(f"⚠️ [{config_settore['settore']}] Rischio Critico: {rischio_pesato}.")
                dettagli_alert.append(f"PIANO AZIONE: {config_settore['consiglio']}")
            
            stato_salute = "CRITICO" if rischio_pesato > soglia_critica else "OTTIMALE"
            if 5.0 < rischio_pesato <= soglia_critica:
                stato_salute = "ATTENZIONE"
                dettagli_alert.append("Trend in crescita: monitoraggio consigliato.")

            # Struttura dati finale per la visualizzazione nella War Room
            report.append({
                "asset": nome_asset,
                "stato": stato_salute,
                "rischio": rischio_pesato,
                "proiezione_impatto": proiezione_30gg,
                "trend_90gg": proiezione_90gg,
                "settore_rilevato": config_settore["descrizione"],
                "segnalazioni": " ".join(dettagli_alert) if dettagli_alert else "Parametri stabili."
            })
        
        logger.info(f"Scan {contesto} completato ({config_settore['settore']}). Asset: {len(report)}")
        return report

def salva_report_certificato(azienda, dati_report, vault):
    """Genera un blob cifrato del report per il download sicuro."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        certificato = f"TS: {timestamp} | AZIENDA: {azienda} | ASSETS_RECAP: {len(dati_report)} | STATUS: VERIFIED"
        return vault.encrypt_data(certificato)
    except Exception as e:
        logger.error(f"Errore generazione certificato cifrato: {e}")
        return None
