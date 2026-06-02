import streamlit as st
import bcrypt
import logging

logger = logging.getLogger("RGD-Alpha.Auth")

def inizializza_sessione():
    """Inizializza le variabili dello stato della sessione di Streamlit se non esistono."""
    if "autenticato" not in st.session_state:
        st.session_state.autenticato = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "email" not in st.session_state:
        st.session_state.email = None
    if "ruolo" not in st.session_state:
        st.session_state.ruolo = None
    if "azienda" not in st.session_state:
        st.session_state.azienda = None

def login_utente(db, email, password):
    """
    Verifica le credenziali dell'utente ed effettua il login.
    Ritorna True se il login ha successo, altrimenti False.
    """
    try:
        utente = db.get_utente_by_email(email)
        if not utente:
            logger.warning(f"Tentativo di login fallito: email non trovata.")
            return False
        
        # Verifica della password hashata con bcrypt
        if bcrypt.checkpw(password.encode(), utente["password_hash"].encode()):
            st.session_state.autenticato = True
            st.session_state.user_id = utente["id"]
            st.session_state.email = utente["email"]
            st.session_state.ruolo = utente["ruolo"]
            st.session_state.azienda = utente["azienda"]
            logger.info(f"Utente {email} autenticato con successo. Ruolo: {utente['ruolo']}")
            return True
        else:
            logger.warning(f"Tentativo di login fallito per {email}: password errata.")
            return False
    except Exception as e:
        logger.error(f"Errore durante la fase di login: {e}")
        return False

def logout_utente():
    """Svuota la sessione ed effettua il logout dell'utente."""
    st.session_state.autenticato = False
    st.session_state.user_id = None
    st.session_state.email = None
    st.session_state.ruolo = None
    st.session_state.azienda = None
    st.rerun()

def richiede_ruolo(ruolo_richiesto):
    """
    Verifica se l'utente loggato ha il ruolo richiesto.
    Se non è autorizzato, interrompe l'esecuzione della pagina di Streamlit.
    """
    if not st.session_state.autenticato:
        st.error("Accesso negato. Effettua prima il login.")
        st.stop()
    
    if ruolo_richiesto == "admin" and st.session_state.ruolo != "admin":
        st.error("Area riservata all'amministratore del sistema.")
        st.stop()