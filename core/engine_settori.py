SETTORI_CONFIG = {
    "FINANZA": {
        "keywords": ["costo", "prezzo", "valore", "asset"],
        "soglia_critica": 5.0,
        "label": "Settore Finanziario",
        "action_plan": "Verificare liquidità e bilanci.",
        "moltiplicatore_rischio": 1.2,
    },
    "LOGISTICA": {
        "keywords": ["scadenza", "lotto", "magazzino"],
        "soglia_critica": 6.0,
        "label": "Settore Logistica",
        "action_plan": "Ottimizzare rotazione stock.",
        "moltiplicatore_rischio": 1.1,
    },
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
                "moltiplicatore": config["moltiplicatore_rischio"],
            }

    # Configurazione di default se non viene riconosciuto un settore specifico
    return {
        "settore": "GENERALE",
        "soglia": 7.0,
        "descrizione": "Analisi Strategica Standard",
        "consiglio": "Monitoraggio periodico dei KPI standard di rischio.",
        "moltiplicatore": 1.0,
    }
