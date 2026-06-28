import logging
from datetime import datetime

# Configurazione Logger per tracciabilità professionale
logger = logging.getLogger("RGD-Alpha.Entities")

class AssetStrategico:
    """
    CLASSE UNIVERSALE RGD-ALPHA: 
    Progettata per adattarsi a qualsiasi documento aziendale (Fatture, Bolle, Prima Nota).
    Utilizza la logica dinamica per prevenire errori di 'unexpected arguments'.
    """
    def __init__(self, id=None, nome="Generico", rischio=0.0, company_id="GENERIC_CORP", **kwargs):
        self.id = id
        self.nome = nome
        self.rischio = rischio
        self.company_id = company_id
        self.data_rilevazione = kwargs.get('data', datetime.now().strftime("%Y-%m-%d"))
        
        # --- MOTORE DINAMICO ---
        # Salva automaticamente qualsiasi altra colonna trovata nel file (es. Pezzi, IBAN, Vettore)
        self.dati_extra = kwargs 
        
        # Inizializziamo i campi per i 5 KPI Predittivi
        self.analisi_predittiva = {}

    def genera_kpi_strategici(self):
        """
        Trasforma i dati grezzi in sentenze strategiche per l'imprenditore.
        Analizza: Solidità, Salute Finanziaria, Rischio Fornitore, Efficienza, Sicurezza.
        """
        # Esempio di logica predittiva interna
        voto_rischio = float(self.rischio)
        
        if voto_rischio > 7:
            conclusione = "CRITICO: Richiede intervento immediato del management."
            previsione = "Rischio di interruzione operativa entro 30 giorni."
        elif voto_rischio < 3:
            conclusione = "SICURO: Asset stabile."
            previsione = "Continuità garantita a lungo termine."
        else:
            conclusione = "MONITORAGGIO: Parametri nella norma."
            previsione = "Stabilità prevista per il prossimo trimestre."

        self.analisi_predittiva = {
            "stato": conclusione,
            "proiezione": previsione,
            "kpi_id": self.id
        }
        return self.analisi_predittiva

class AssetDiMercato(AssetStrategico):
    """
    SETTORE LOGISTICA & MAGAZZINO (Bolle, Carico/Scarico, DDT)
    Adattato per riconoscere i documenti di trasporto e registri movimenti.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Mapping Universale: cerca 'Quantita', 'Pezzi', o il nuovo 'Codice_SKU'
        self.quantita = kwargs.get('quantita', kwargs.get('Quantita', kwargs.get('Pezzi', 0)))
        self.sku = kwargs.get('Codice_SKU', kwargs.get('SKU', 'N/D'))
        self.ubicazione = kwargs.get('Ubicazione', 'Magazzino Centrale')

class AssetDiValore(AssetStrategico):
    """
    SETTORE FINANCE & CONTABILITÀ (Fatture, Prima Nota, Bilancio)
    Adattato per gestire flussi di cassa e pagamenti.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Mapping Universale: cerca 'Importo', 'Lordo', o 'Costo_Unitario'
        self.prezzo = kwargs.get('prezzo', kwargs.get('Importo', kwargs.get('Costo_Unitario', 0.0)))
        self.stato_pagamento = kwargs.get('stato', kwargs.get('Stato_Qualita', kwargs.get('Condizione', 'In attesa')))
        self.valuta = kwargs.get('Valuta', 'EUR')

class AssetDiRelazione(AssetStrategico):
    """
    SETTORE CRM & STAKEHOLDERS (Clienti, Fornitori, Contratti)
    Adattato per valutare la solidità dei rapporti commerciali.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Mapping Universale: identifica il partner commerciale
        self.partner = kwargs.get('Fornitore_Origine', kwargs.get('Cliente', kwargs.get('Ragione_Sociale', 'Privato')))
        self.livello_servizio = kwargs.get('rischio', 5.0)
