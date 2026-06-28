# FILE: experimental_modules/engine_settori.py
# SCOPO: Mappatura intelligente e configurazione dinamica del motore RGD-Alpha

SETTORI_CONFIG = {
    "PRIMARIO_ALIMENTARE": {
        "keywords": ["scadenza", "lotto", "haccp", "temperatura", "fresco", "conservazione"],
        "soglia_critica": 6.5,  # Più severo per via della deperibilità
        "label": "Qualità e Deperibilità",
        "action_plan": "Verificare immediatamente scadenze imminenti e integrità catena del freddo.",
        "moltiplicatore_rischio": 1.3
    },
    "SECONDARIO_MANIFATTURA": {
        "keywords": ["taglia", "materia prima", "produzione", "stock", "pezzi", "semilavorato"],
        "soglia_critica": 7.5,
        "label": "Continuità Produttiva",
        "action_plan": "Monitorare colli di bottiglia in produzione e disponibilità materie prime.",
        "moltiplicatore_rischio": 1.1
    },
    "TERZIARIO_LOGISTICA": {
        "keywords": ["bolla", "ddt", "targa", "consegna", "ritardo", "vettore", "spedizione"],
        "soglia_critica": 8.0,
        "label": "Efficienza Distributiva",
        "action_plan": "Analizzare lead time dei vettori e ottimizzare rotte di distribuzione.",
        "moltiplicatore_rischio": 1.0
    }
}

def analizza_e_configura_motore(lista_colonne):
    """
    Analizza i metadati del file (colonne) eliminando spazi e standardizzando 
    il testo per garantire il riconoscimento del settore, ispezionando anche 
    le chiavi annidate in dati_extra se presenti.
    """
    # Puliamo e rendiamo minuscole tutte le colonne singolarmente, togliendo spazi vuoti
    colonne_pulite = [str(col).strip().lower() for col in lista_colonne]
    
    # --- INTEGRAZIONE STRATEGICA 2026 ---
    # Se l'ingestore ha inserito 'dati_extra' tra le chiavi, espandiamo l'analisi
    # per intercettare keyword annidate come 'scadenza' o 'lotto'
    if "dati_extra" in colonne_pulite:
        # Aggiungiamo esplicitamente le keyword note di dati_extra per l'ispezione delle stringhe
        colonne_pulite.extend(["scadenza", "lotto", "id_asset"])
    
    # Uniamo in un'unica stringa per il controllo delle keyword
    colonne_str = " ".join(colonne_pulite)
    
    for settore, config in SETTORI_CONFIG.items():
        # Controlla se almeno una keyword del settore è presente nelle colonne pulite
        if any(key in colonne_str for key in config["keywords"]):
            return {
                "settore": settore,
                "soglia": config["soglia_critica"],
                "descrizione": config["label"],
                "consiglio": config["action_plan"],
                "moltiplicatore": config["moltiplicatore_rischio"]
            }
            
    # Configurazione di default se non viene riconosciuto un settore specifico
    return {
        "settore": "GENERALE",
        "soglia": 7.0,
        "descrizione": "Analisi Strategica Standard",
        "consiglio": "Monitoraggio periodico dei KPI standard di rischio.",
        "moltiplicatore": 1.0
    }
