import pandas as pd
import os
from datetime import datetime
import logging
from core.secure_vault import SecureVault
from core.entities import AssetDiMercato, AssetDiValore, AssetDiRelazione, AssetStrategico
from core.database import DatabaseAziendale

logger = logging.getLogger("RGD-Alpha.Ingestor")

class IngestoreDati:
    """
    INGESTORE UNIVERSALE RGD-ALPHA:
    Sistema adattivo con validazione preventiva per prevenire crash.
    """
    def __init__(self, key_path="core/security/vault.key"):
        self.vault = SecureVault(key_path=key_path)
        self.db = DatabaseAziendale()
        
        # Dizionario esteso per mappare i file reali ai campi del sistema
        self.mappa_sinonimi = {
            'quantita': ['quantita', 'pezzi', 'qta', 'stock', 'unita', 'Quantita', 'Giacenza'],
            'valore': ['prezzo', 'importo', 'lordo', 'valore', 'costo', 'ammontare', 'Costo_Unitario', 'prezzo_acquisto'],
            'rischio': ['rischio', 'impatto', 'criticità', 'priorità', 'Rischio_Logistico', 'Risk_Factor'],
            'stato': ['stato', 'condizione', 'status', 'pagamento', 'disponibilita', 'Stato_Qualita']
        }

    def _valida_dati_critici(self, df):
        """
        DATA VALIDATOR: Controlla se il file ha i requisiti minimi per non rompere il sistema.
        Ritorna (True, message) o (False, error_message).
        """
        if df.empty:
            return False, "Il file caricato è vuoto."
        
        # Cerchiamo se esiste almeno una colonna che assomigli a un 'nome' o 'descrizione'
        nomi_possibili = ['nome', 'descrizione', 'prodotto', 'asset', 'Descrizione_Asset', 'SKU']
        if not any(col in [c.lower() for c in df.columns] for col in nomi_possibili):
            return False, "Non trovo una colonna 'Nome' o 'Prodotto'. Controlla le intestazioni del file."

        return True, "Validazione superata."

    def _auto_rilevamento_settore(self, colonne):
        """Analizza le intestazioni per capire se è Logistica, Finance o Relazioni."""
        colonne_lower = [str(c).lower() for c in colonne]
        
        if any(term in colonne_lower for term in ['fattura', 'iban', 'lordo', 'costo_unitario']):
            return "FINANCE", AssetDiValore
        if any(term in colonne_lower for term in ['bolla', 'ddt', 'magazzino', 'quantita', 'sku', 'ubicazione', 'giacenza']):
            return "LOGISTICS", AssetDiMercato
        if any(term in colonne_lower for term in ['cliente', 'fornitore', 'crm', 'fornitore_origine']):
            return "RELATIONS", AssetDiRelazione
        
        return "GENERAL", AssetStrategico

    def _estrai_dato(self, row, categoria_chiave, default=0):
        """Cerca il dato usando i sinonimi definiti sopra."""
        for sinonimo in self.mappa_sinonimi.get(categoria_chiave, []):
            val = row.get(sinonimo)
            if val is not None and not pd.isna(val):
                return val
        return default

    def elabora_csv(self, file_path, company_id):
        asset_list = [] 
        
        if not os.path.exists(file_path):
            logger.error(f"File {file_path} non trovato.")
            return asset_list

        try:
            # Lettura del file
            df = pd.read_csv(file_path)
            
            # --- ESECUZIONE VALIDATORE ---
            valido, messaggio = self._valida_dati_critici(df)
            if not valido:
                logger.warning(f"Validazione fallita per {company_id}: {messaggio}")
                # Potresti voler lanciare un'eccezione qui per mostrarla in Streamlit
                return asset_list

            # Rilevamento automatico del reparto
            settore_nome, ClasseAsset = self._auto_rilevamento_settore(df.columns)
            self.db.registra_caricamento(company_id, f"Ingestione {settore_nome}", os.path.basename(file_path))

            for _, row in df.iterrows():
                dati_riga = row.to_dict()
                
                # Normalizzazione campi fondamentali per evitare crash in engine.py
                dati_riga['id_asset'] = row.get('ID_Movimento', row.get('id', row.get('ID', 'N/D')))
                dati_riga['nome'] = row.get('Descrizione_Asset', row.get('nome', row.get('prodotto', 'Asset_Generico')))
                
                # Pulizia rischio: assicuriamoci che sia un numero tra 0 e 10
                try:
                    rischio_raw = self._estrai_dato(row, 'rischio', 5.0)
                    dati_riga['rischio'] = float(rischio_raw)
                except:
                    dati_riga['rischio'] = 5.0 # Fallback se il dato non è numerico

                dati_riga['company_id'] = company_id
                dati_riga['data'] = row.get('Data_Registrazione', row.get('data', datetime.now().strftime("%Y-%m-%d")))

                try:
                    # Inizializzazione della classe
                    nuovo_asset = ClasseAsset(**dati_riga)
                    if hasattr(nuovo_asset, 'genera_kpi_strategici'):
                        nuovo_asset.genera_kpi_strategici()
                    
                    asset_list.append(nuovo_asset)
                except Exception as e:
                    logger.debug(f"Salto riga per errore formato: {e}")

        except Exception as e:
            logger.error(f"Errore critico durante l'elaborazione del file: {e}")
        
        return asset_list