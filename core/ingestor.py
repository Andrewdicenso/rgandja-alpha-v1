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
    Sistema adattivo con scansione attiva degli header per tracciati SAP, Oracle e Excel custom.
    """
    def __init__(self, key_path="core/security/vault.key"):
        self.vault = SecureVault(key_path=key_path)
        self.db = DatabaseAziendale()
        
        # Mappatura estesa con termini SAP e Internazionali
        self.mappa_sinonimi = {
            'nome': ['nome', 'prodotto', 'descrizione', 'materiale', 'articolo', 'asset', 'material', 'description', 'item', 'sku', 'descrizione_asset', 'material description', 'testo breve materiale'],
            'quantita': ['quantita', 'pezzi', 'qta', 'stock', 'unita', 'quantity', 'qty', 'giacenza', 'volume', 'quantità'],
            'valore': ['prezzo', 'importo', 'lordo', 'valore', 'costo', 'ammontare', 'amount', 'price', 'value', 'costo_unitario', 'total_cost', 'valore totale', 'val.totale', 'prezzo totale'],
            'rischio': ['rischio', 'impatto', 'criticita', 'priorita', 'risk', 'priority', 'risk_factor', 'score', 'livello rischio'],
            'stato': ['stato', 'condizione', 'status', 'pagamento', 'disponibilita', 'availability', 'state', 'stato magazzino']
        }

    def _pulisci_e_riallinea_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        SCANSIONE ADATTIVA: Cerca la riga degli header ovunque si trovi 
        (fondamentale per file SAP/Excel con metadati o titoli in cima).
        """
        # Scansioniamo le prime 15 righe alla ricerca della vera riga "intestazione"
        for i in range(min(len(df), 15)):
            riga_corrente = [str(x).lower().strip() for x in df.iloc[i].values if pd.notna(x)]
            
            punteggio_header = 0
            tutti_i_sinonimi = [item for sublist in self.mappa_sinonimi.values() for item in sublist]
            
            for cella in riga_corrente:
                if any(sin in cella for sin in tutti_i_sinonimi):
                    punteggio_header += 1
            
            # Se troviamo almeno 2 match, abbiamo trovato la riga degli header
            if punteggio_header >= 2:
                df.columns = df.iloc[i]
                df = df[i+1:].reset_index(drop=True)
                logger.info(f"✅ Header riallineato con successo alla riga {i}")
                break
        
        # Rimuove colonne vuote o non identificate
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed')]
        return df

    def _trova_colonna_vera(self, df_columns: List[str], categoria: str) -> Optional[str]:
        """Trova il nome esatto della colonna partendo dai sinonimi."""
        colonne_pulite = {str(c).strip().lower(): str(c) for c in df_columns}
        for sinonimo in self.mappa_sinonimi.get(categoria, []):
            if sinonimo.lower() in colonne_pulite:
                return colonne_pulite[sinonimo.lower()]
        return None

    def _valida_dati_critici(self, df: pd.DataFrame):
        """Validazione preventiva per assicurarsi che il file sia leggibile."""
        if df.empty:
            return False, "Il file caricato è vuoto."
        
        if not self._trova_colonna_vera(df.columns, 'nome'):
            return False, "Colonna Prodotto/Materiale non trovata. Controlla le intestazioni del file."

        return True, "Validazione superata."

    def _auto_rilevamento_settore(self, colonne):
        """Identifica il settore aziendale in base alle intestazioni."""
        c_low = [str(c).lower() for c in colonne]
        if any(t in c_low for t in ['fattura', 'iban', 'lordo', 'iva', 'invoice', 'billing']):
            return "FINANCE", AssetDiValore
        if any(t in c_low for t in ['bolla', 'ddt', 'magazzino', 'sku', 'giacenza', 'warehouse', 'stock']):
            return "LOGISTICS", AssetDiMercato
        if any(t in c_low for t in ['cliente', 'fornitore', 'crm', 'vendor', 'customer', 'partner']):
            return "RELATIONS", AssetDiRelazione
        return "GENERAL", AssetStrategico

    def _pulisci_numero(self, val, default=0.0):
        """Trasforma stringhe sporche (es: '1.200,50 €') in numeri float validi."""
        if pd.isna(val): return default
        s = str(val).replace('€', '').replace('$', '').strip()
        # Gestione formati europei (punti migliaia e virgole decimali)
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        try:
            # Estrae solo i caratteri numerici e il punto
            clean_s = ''.join(c for c in s if c.isdigit() or c == '.' or c == '-')
            return float(clean_s) if clean_s else default
        except:
            return default

    def elabora_csv(self, file_path, company_id):
        """Funzione principale di elaborazione file."""
        asset_list = [] 
        if not os.path.exists(file_path): return asset_list

        try:
            # 1. Caricamento flessibile del file
            df = pd.read_csv(file_path, sep=None, engine='python', on_bad_lines='skip')
            
            # 2. Riallineamento Header (per file SAP con titoli in cima)
            df = self._pulisci_e_riallinea_df(df)

            # 3. Validazione
            valido, messaggio = self._valida_dati_critici(df)
            if not valido:
                logger.warning(f"Validazione fallita: {messaggio}")
                return asset_list

            # 4. Rilevamento Reparto e Colonne
            settore, ClasseAsset = self._auto_rilevamento_settore(df.columns)
            col_nome = self._trova_colonna_vera(df.columns, 'nome')
            col_rischio = self._trova_colonna_vera(df.columns, 'rischio')
            col_valore = self._trova_colonna_vera(df.columns, 'valore')

            # 5. Iterazione e Creazione Asset
            for _, row in df.iterrows():
                dati = row.to_dict()
                
                # Normalizzazione campi obbligatori
                dati['nome'] = str(row.get(col_nome, "Asset_Sconosciuto")).strip()
                dati['asset'] = dati['nome']
                dati['rischio'] = self._pulisci_numero(row.get(col_rischio), 5.0)
                dati['valore_asset'] = self._pulisci_numero(row.get(col_valore), 0.0)
                dati['company_id'] = company_id
                dati['data'] = datetime.now().strftime("%Y-%m-%d")

                try:
                    nuovo_asset = ClasseAsset(**dati)
                    if hasattr(nuovo_asset, 'genera_kpi_strategici'):
                        nuovo_asset.genera_kpi_strategici()
                    asset_list.append(nuovo_asset)
                except Exception as e:
                    continue # Salta righe malformate

            # Registrazione nel database
            self.db.registra_caricamento(company_id, f"Analisi {settore}", os.path.basename(file_path))

        except Exception as e:
            logger.error(f"Errore critico Ingestore: {e}")
        
        return asset_list