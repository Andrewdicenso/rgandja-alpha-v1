import os
import logging
import pandas as pd
from typing import Optional, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# Configurazione Logger
logger = logging.getLogger("RGD-Alpha.Database")

# Carica le variabili di ambiente dal file .env
load_dotenv()

class DatabaseAziendale:
    def __init__(self):
        """Inizializza la connessione al database Cloud Supabase (PostgreSQL)."""
        try:
            self.url = os.getenv("SUPABASE_URL")
            self.key = os.getenv("SUPABASE_KEY")
            
            if not self.url or not self.key:
                raise ValueError("SUPABASE_URL o SUPABASE_KEY mancanti nel file .env!")
            
            # Client ufficiale Supabase
            self.client: Client = create_client(self.url, self.key)
            logger.info("🛡️ Connessione al Database Supabase RGD-Alpha stabilita con successo!")
            
        except Exception as e:
            logger.critical(f"❌ Fallimento connessione Supabase: {e}")
            raise

    # --- GESTIONE UTENTI ---
    def crea_utente(self, email: str, password_hash: str, ruolo: str = "user", azienda: str = None) -> dict:
        """Crea un nuovo utente nel database Supabase."""
        try:
            payload = {
                "email": email.lower(),
                "password": password_hash,
                "ruolo": ruolo,
                "azienda": azienda or "AZ-TMP"
            }
            res = self.client.table("utenti").insert(payload).execute()
            
            if res.data:
                user_id = res.data[0]["id"]
                # Se l'azienda non era specificata, aggiorna con AZ-<id>
                if not azienda:
                    azienda_code = f"AZ-{user_id}"
                    self.client.table("utenti").update({"azienda": azienda_code}).eq("id", user_id).execute()
                    res.data[0]["azienda"] = azienda_code
                return res.data[0]
            return None
        except Exception as e:
            logger.error(f"Errore creazione utente: {e}")
            raise

    def get_utente_by_email(self, email: str) -> dict:
        """Recupera un utente in modo istantaneo tramite query diretta su Supabase."""
        try:
            res = self.client.table("utenti").select("*").eq("email", email.lower()).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None
        except Exception as e:
            logger.error(f"Errore recupero utente per email {email}: {e}")
            return None

    def get_utente_by_id(self, user_id:any) -> dict:
        user_id = str(user_id).replace("AZ-", "")
        try:
            res = self.client.table("utenti").select("*").eq("id", user_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None
        except Exception as e:
            logger.error(f"Errore recupero utente ID {user_id}: {e}")
            return None

    # --- REGISTRAZIONE ATTIVITÀ E ASSET ---
    def registra_caricamento(self, user_id: int, contesto: str, nome_file: str):
        """Registra un log nel database quando l'utente carica un file (SAP/Excel)."""
        try:
            utente = self.get_utente_by_id(user_id)
            azienda = utente["azienda"] if utente else "N/A"
            
            payload = {
                "user_id": user_id,
                "azienda": azienda,
                "contesto": contesto,
                "nome_file": nome_file
            }
            self.client.table("log_caricamenti").insert(payload).execute()
            logger.info(f"📁 Log caricamento registrato: {nome_file} da user {user_id}")
        except Exception as e:
            logger.error(f"Errore registrazione caricamento: {e}")

    def salva_asset(self, user_id: int, nome_asset: str, rischio: float, **kwargs):
        """Salva le metriche di un asset nell'archivio storico degli asset."""
        try:
            utente = self.get_utente_by_id(user_id)
            company_id = utente["azienda"] if utente else f"AZ-{user_id}"
            
            payload = {
                "user_id": user_id,
                "company_id": company_id,
                "nome": nome_asset,
                "tipo": kwargs.get('tipo', 'Generico'),
                "rischio": float(rischio),
                "momentum": kwargs.get('momentum', 'Stabile'),
                "volatilita": float(kwargs.get('volatilita', 0.0))
            }
            self.client.table("asset_logs").insert(payload).execute()
            logger.info(f"📊 Asset registrato: {nome_asset} con rischio {rischio}")
        except Exception as e:
            logger.error(f"Errore salvataggio asset: {e}")

    # --- CALCOLO KPI REALI ---
    def calcola_e_salva_kpi_correnti(self, user_id: int) -> dict:
        """Calcola la solidità e l'impatto aziendale basandosi sugli ultimi asset salvati."""
        try:
            # Query diretta a Supabase sugli asset dell'utente
            res = self.client.table("asset_logs").select("rischio").eq("user_id", user_id).execute()
            
            if not res.data or len(res.data) == 0:
                return {"solidita": 100.0, "impatto_30gg": "STABILE", "rischio_medio": 0.0}

            # Estrazione dei valori di rischio
            rischi = [row["rischio"] for row in res.data if row.get("rischio") is not None]
            
            if not rischi:
                return {"solidita": 100.0, "impatto_30gg": "STABILE", "rischio_medio": 0.0}

            rischio_medio = sum(rischi) / len(rischi)
            
            # Calcolo formula solidità (scala 0 - 100)
            solidita = round(100 - (rischio_medio * 10), 1)
            solidita = max(min(solidita, 100.0), 0.0)

            impatto = "CRITICO" if rischio_medio > 7 else "ATTENZIONE" if rischio_medio > 4 else "STABILE"

            return {
                "solidita": solidita,
                "impatto_30gg": impatto,
                "rischio_medio": round(rischio_medio, 2)
            }
        except Exception as e:
            logger.error(f"Errore calcolo KPI: {e}")
            return {"solidita": 0.0, "impatto_30gg": "ERRORE", "rischio_medio": 0.0}

    # --- METODI PER PANNELLO ADMIN (SUPERVISIONE) ---
    def supervisione_admin_metriche_globali(self) -> pd.DataFrame:
        """Restituisce il DataFrame degli utenti registrati per la dashboard Admin."""
        try:
            res = self.client.table("utenti").select("email, ruolo, azienda, data_creazione").execute()
            return pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            logger.error(f"Errore supervisione admin utenti: {e}")
            return pd.DataFrame()

    def recupera_attivita_globale(self) -> pd.DataFrame:
        """Restituisce il DataFrame di tutti gli asset log per la dashboard Admin."""
        try:
            res = self.client.table("asset_logs").select("*").execute()
            return pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            logger.error(f"Errore recupero attività globale: {e}")
            return pd.DataFrame()

    def recupera_log_caricamenti_admin(self) -> pd.DataFrame:
        """Restituisce il DataFrame di tutti i caricamenti effettuati."""
        try:
            res = self.client.table("log_caricamenti").select("*").execute()
            return pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            logger.error(f"Errore log caricamenti admin: {e}")
            return pd.DataFrame()

    def recupera_storia_caricamenti(self, user_id: int) -> pd.DataFrame:
        """Recupera la cronologia dei file caricati dall'utente specifico."""
        try:
            res = self.client.table("log_caricamenti").select("*").eq("user_id", user_id).order("data_creazione", desc=True).execute()
            return pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            logger.error(f"Errore recupero storia: {e}")
            return pd.DataFrame()