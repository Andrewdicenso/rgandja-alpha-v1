import os
from google import genai
from google.genai import types


def genera_executive_report_ia(
    report_analisi: list, kpi_reali: dict, resilience_score: float
) -> str:
    """
    Interroga il client Gemini per generare il report esecutivo e strategico
    basato sui dati elaborati dalla War Room.
    """
    # Recupera la chiave API dall'ambiente o dai secrets di Streamlit
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ Errore di configurazione: Chiave API di Gemini non trovata nelle variabili d'ambiente."

    try:
        client = genai.Client(api_key=api_key)

        # Preparazione del payload testuale con i dati della War Room
        sintesi_asset = "\n".join(
            [
                f"- Asset: {a.get('asset')} | Stato: {a.get('stato')} | Rischio: {a.get('rischio')} | Trend: {a.get('trend_90gg')}"
                for a in report_analisi
            ]
        )

        prompt = f"""
        Agisci come Chief Strategy Officer (CSO) per una piattaforma di Business Intelligence industriale.
        Analizza i seguenti KPI e lo stato degli asset di magazzino calcolati dalla War Room:

        [KPI VITALI]
        - Solidità Aziendale: {kpi_reali.get('solidita', 0)}%
        - Rischio Medio: {kpi_reali.get('rischio_medio', 0)}/10
        - Resilienza Operativa: {resilience_score}%

        [STATO DEGLI ASSET]
        {sintesi_asset}

        Genera un Executive Summary e una diagnostica strategica formale (in Markdown) che includa:
        1. Una sintesi direzionale sullo stato di salute e sui Single Point of Failure (SPOF).
        2. Una proiezione del rischio a medio termine.
        3. Direttive prescrittive immediate per il board aziendale.
        """

        # Utilizziamo il modello corrente supportato per i nuovi rilasci
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="Sei un CSO virtuale rigoroso, professionale ed esperto di risk management industriale.",
                temperature=0.3,
            ),
        )

        return response.text

    except Exception as e:
        return f"❌ Errore durante la comunicazione con il motore IA: {str(e)}"
