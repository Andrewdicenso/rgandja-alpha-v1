import pandas as pd
import os
from datetime import datetime
import logging
from core.secure_vault import SecureVault
from core.entities import AssetDiMercato, AssetDiValore, AssetDiRelazione, AssetStrategico
from core.database import DatabaseAziendale
from typing import Any, List, Optional

logger = logging.getLogger("RGD-Alpha.Ingestor")

class IngestoreDati:
    """
    INGESTORE UNIVERSALE RGD-ALPHA (Enterprise Grade):
    Sistema adattivo con supporto esteso per tracciati SAP, Oracle e Excel custom.
    """
    def __init__(self, key_path="core/security/vault.key"):
        self.vault = SecureVault(key_path=key_path)
        self.db = DatabaseAziendale()
        
        # Mappatura estesa con termini SAP e Internazionali
        self.mappa_sinonimi = {
            'nome': ['nome', 'prodotto', 'descrizione', 'materiale', 'articolo', 'asset', 'material', 'description', 'item', 'sku', 'descrizione_asset'],
            'quantita': ['quantita', 'pezzi', 'qta', 'stock', 'unita', 'quantity', 'qty', 'giacenza', 'volume'],
            'valore': ['prezzo', 'importo', 'lordo', 'valore', 'costo', 'ammontare', 'amount', 'price', 'value', 'costo_unitario', 'total_cost'],
            'rischio': ['rischio', 'impatto', 'criticita', 'priorita', 'risk', 'priority', 'risk_factor', 'score'],
            'stato': ['stato', 'condizione', 'status', 'pagamento', 'disponibilita', 'availability', 'state']
        }

    def _trova_colonna_vera(self, df_columns: List[str], categoria: str) -> Optional[str]:
        """Trova il nome esatto della colonna nel file partendo da un sinonimo."""
        colonne_pulite = {str(c).strip().lower(): str(c) for c in df_columns}
        for sinonimo in self.mappa_sinonimi.get(categoria, []):
            if sinonimo.lower() in colonne_pulite:
                return colonne_pulite[sinonimo.lower()]
        return None

    def _valida_dati_critici(self, df: pd.DataFrame):
        """Validazione preventiva con logica fuzzy."""
        if df.empty:
            return False, "Il file caricato è vuoto."
        
        # Un file deve avere almeno un 'nome' per essere processato
        if not self._trova_colonna_vera(df.columns, 'nome'):
            return False, f"Colonna Identificativa non trovata. Il file deve contenere uno di questi: {self.mappa_sinonimi['nome']}"

        return True, "Validazione superata."

    def _auto_rilevamento_settore(self, colonne):
        """Rilevamento euristico del settore aziendale."""
        c_low = [str(c).lower() for c in colonne]
        if any(t in c_low for t in ['fattura', 'iban', 'lordo', 'iva', 'invoice', 'billing']):
            return "FINANCE", AssetDiValore
        if any(t in c_low for t in ['bolla', 'ddt', 'magazzino', 'sku', 'giacenza', 'warehouse', 'stock']):
            return "LOGISTICS", AssetDiMercato
        if any(t in c_low for t in ['cliente', 'fornitore', 'crm', 'vendor', 'customer', 'partner']):
            return "RELATIONS", AssetDiRelazione
        return "GENERAL", AssetStrategico

    def elabora_csv(self, file_path, company_id):
        asset_list = [] 
        if not os.path.exists(file_path):
            return asset_list

        try:
            # Caricamento flessibile (gestisce diversi separatori comuni nei CSV SAP)
            try:
                df = pd.read_csv(file_path, sep=None, engine='python')
            except:
                df = pd.read_csv(file_path)

            valido, messaggio = self._valida_dati_critici(df)
            if not valido:
                logger.warning(f"Validazione fallita: {messaggio}")
                return asset_list

            settore, ClasseAsset = self._auto_rilevamento_settore(df.columns)
            
            # Trova le colonne chiave una volta sola
            col_nome = self._trova_colonna_vera(df.columns, 'nome')
            col_rischio = self._trova_colonna_vera(df.columns, 'rischio')
            col_valore = self._trova_colonna_vera(df.columns, 'valore')

            for _, row in df.iterrows():
                dati = row.to_dict()
                
                # Mappatura dei campi per le classi Entity
                dati['nome'] = row.get(col_nome, "Asset_Sconosciuto")
                dati['asset'] = dati['nome'] # Alias per compatibilità
                
                # Normalizzazione Rischio (scala 0-10)
                try:
                    val_r = row.get(col_rischio, 5.0)
                    dati['rischio'] = float(val_r) if pd.notna(val_r) else 5.0
                except:
                    dati['rischio'] = 5.0

                # Dati Extra e Company
                dati['company_id'] = company_id
                dati['data'] = datetime.now().strftime("%Y-%m-%d")

                try:
                    nuovo_asset = ClasseAsset(**dati)
                    if hasattr(nuovo_asset, 'genera_kpi_strategici'):
                        nuovo_asset.genera_kpi_strategici()
                    asset_list.append(nuovo_asset)
                except Exception as e:
                    continue # Salta righe corrotte

            self.db.registra_caricamento(company_id, f"Analisi {settore}", os.path.basename(file_path))

        except Exception as e:
            logger.error(f"Errore critico Ingestore: {e}")
        
        return asset_list
