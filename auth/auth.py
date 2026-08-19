import os
import logging
import bcrypt
import streamlit as st
from streamlit import secrets
from supabase import create_client
from typing import Optional, Any

# ==========================================
# 1. CONFIGURAZIONE LOGGING & CLIENT
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_supabase():
    """Inizializza il client Supabase con gestione errori."""
    try:
        url = secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
        key = secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            st.error("Configurazione Supabase mancante nei Secrets o .env")
            st.stop()
            
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Errore critico inizializzazione Supabase: {e}")
        st.stop()

supabase = init_supabase()

# ==========================================
# 2. GESTIONE SESSIONE
# ==========================================
def inizializza_sessione():
    """Inizializza lo stato della sessione in modo atomico."""
    defaults = {
        "autenticato": False,
        "user_id": None,
        "email": None,
        "ruolo": None,
        "azienda": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ==========================================
# 3. LOGICA DI AUTENTICAZIONE
# ==========================================
def login_utente(db: Any, email: str, password: str) -> bool:
    """
    Verifica le credenziali ed effettua il login.
    Args:
        db: Istanza del DatabaseAziendale
        email: Email inserita
        password: Password in chiaro
    """
    try:
        utente = db.get_utente_by_email(email)
        
        if not utente:
            logger.warning(f"Login fallito: {email} non trovato.")
            return False
        
        # Verifica della password hashata
        password_hash = utente.get("password_hash")
        if not password_hash:
            logger.error(f"Errore database: password_hash mancante per {email}")
            return False

        if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            # Aggiornamento stato sessione
            st.session_state.update({
                "autenticato": True,
                "user_id": utente.get("id"),
                "email": utente.get("email"),
                "ruolo": utente.get("ruolo"),
                "azienda": utente.get("azienda")
            })
            logger.info(f"Login successo: {email} (Ruolo: {utente.get('ruolo')})")
            return True
        else:
            logger.warning(f"Login fallito: Password errata per {email}")
            return False
            
    except Exception as e:
        logger.error(f"Errore durante il login per {email}: {str(e)}")
        st.error("Si è verificato un errore tecnico durante l'accesso.")
        return False

def logout_utente():
    """Reset completo della sessione."""
    st.session_state.clear() # Svuota tutto per sicurezza
    st.rerun()

# ==========================================
# 4. CONTROLLO ACCESSI (RBAC)
# ==========================================
def richiede_ruolo(ruolo_richiesto: str):
    """
    Blocca l'esecuzione se l'utente non ha i permessi.
    """
    if not st.session_state.get("autenticato"):
        st.warning("Eseguire il login per accedere a questa sezione.")
        st.stop()
    
    # Se richiesto admin, solo gli admin passano
    if ruolo_richiesto == "admin" and st.session_state.get("ruolo") != "admin":
        st.error("🚫 Area Riservata agli Amministratori.")
        st.stop()