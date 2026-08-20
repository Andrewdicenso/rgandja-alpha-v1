import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px
import bcrypt
import streamlit as st
from dotenv import load_dotenv

# --- MODULI CORE & AUTH ---
from core.ingestor import IngestoreDati
from core.engine import DataGateway, salva_report_certificato
from core.database import DatabaseAziendale
from auth.auth import inizializza_sessione, login_utente, logout_utente

# ==========================================
# 1. CONFIGURAZIONE BASE & PATHS
# ==========================================
load_dotenv()
PROJECT_ROOT = Path(__file__).parent
DATA_ROOT = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_ROOT / "uploads"

# Creazione cartelle necessarie
for folder in [UPLOAD_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Configurazione Pagina (Deve essere la prima chiamata Streamlit)
st.set_page_config(
    page_title="RGD-Alpha | War Room Strategica",
    layout="wide",
    page_icon="🛡️"
)

# Inizializzazione variabili sessione
inizializza_sessione()

# ==========================================
# 2. CSS ENTERPRISE (Iniezione Stili)
# ==========================================
st.markdown("""
    <style>
    .kpi-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #007BFF; margin-bottom: 15px; }
    .kpi-box-critical { background-color: #fff5f5; padding: 20px; border-radius: 10px; border-left: 5px solid #dc3545; margin-bottom: 15px; }
    .ai-reasoning { background: #0e1117; border: 1px solid #d4af37; padding: 25px; border-radius: 15px; color: #e2e8f0; line-height: 1.6; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .crew-box { padding:15px; border-radius:10px; background:rgba(255,255,255,0.02); margin-bottom:10px; border-left: 5px solid #ccc; }
    </style>
""", unsafe_allow_html=True)

# Inizializzazione Client Database
db = DatabaseAziendale()

# ==========================================
# 3. LOGICA DI SUPPORTO AUTH
# ==========================================
def registra_nuovo_utente(email, pwd, conf):
    """Gestisce la creazione sicura di un nuovo utente."""
    if pwd != conf:
        st.error("Le password non coincidono!")
        return
    if len(pwd) < 6:
        st.error("La password deve essere di almeno 6 caratteri.")
        return
    
    # Hashing sicuro della password (bcrypt)
    pwd_hash = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        # Determina il ruolo in base all'email admin
        ruolo = "admin" if email.lower() == "andrewdicenso@libero.it" else "user"
        
        # Tenta la creazione nel DB
        nuovo_utente = db.crea_utente(email=email, password_hash=pwd_hash, ruolo=ruolo)
        if nuovo_utente:
            st.success("✅ Registrazione completata! Ora puoi accedere.")
            st.balloons()
        else:
            st.error("Errore: L'utente potrebbe già esistere.")
    except Exception as e:
        st.error(f"Errore tecnico durante la registrazione: {e}")

# ==========================================
# 4. CONTROLLO ACCESSO (BLOCKING)
# ==========================================
if not st.session_state.autenticato:
    tab_login, tab_register = st.tabs(["🔐 Login", "🆕 Registrazione"])
    
    with tab_login:
        st.title("🔐 Accesso Utente")
        e_login = st.text_input("Email", key="l_email").strip()
        p_login = st.text_input("Password", type="password", key="l_pwd").strip()
        if st.button("Accedi"):
            if login_utente(db, e_login, p_login): 
                st.rerun()
            else: 
                st.error("Credenziali errate.")
                
    with tab_register:
        st.title("🆕 Crea account Beta")
        e_reg = st.text_input("Email", key="r_email").strip()
        p_reg = st.text_input("Password", type="password", key="r_pwd").strip()
        c_reg = st.text_input("Conferma", type="password", key="r_conf").strip()
        if st.button("Registrati"): 
            registra_nuovo_utente(e_reg, p_reg, c_reg)
            
    st.stop() # BLOCCA l'esecuzione del resto dell'app per i non loggati

# ==========================================
# 5. DASHBOARD POST-LOGIN (Solo per autenticati)
# ==========================================
user_id = st.session_state.user_id
azienda = st.session_state.azienda
ruolo = st.session_state.ruolo
is_admin = (ruolo == "admin")

# --- SIDEBAR NAV ---
st.sidebar.title("🛡️ RGD-ALPHA")
st.sidebar.write(f"Operatore: **{st.session_state.email}**")
st.sidebar.write(f"Azienda: **{azienda}**")

menu = ["📊 War Room Strategica", "📜 Archivio Storico"]
if is_admin: 
    menu.insert(0, "🕵️ Centrale Admin")

scelta = st.sidebar.radio("Navigazione", menu)

if st.sidebar.button("Logout"): 
    logout_utente()

# --- LOGICA PAGINE ---
if scelta == "📊 War Room Strategica":
    st.title(f"🚀 War Room Strategica: {azienda}")
    
    with st.sidebar:
        with st.expander("⚙️ CALIBRAZIONE EMA", expanded=True):
            w1 = st.slider("Peso Presente (W1)", 0.1, 1.0, 0.7)
            w2 = st.slider("Peso Storico (W2)", 0.1, 1.0, 0.3)
        with st.expander("🚨 STRESS TEST", expanded=True):
            ritardo = st.slider("Ritardo Fornitori (Giorni)", 0, 30, 0)
            f_stress = 1.0 + (ritardo / 50.0)

    uploaded_file = st.file_uploader("Carica inventario CSV", type=["csv"])
    if uploaded_file:
        # Crea sottocartella azienda se non esiste
        azienda_safe = str(azienda).replace(" ", "_")
        path = UPLOAD_DIR / azienda_safe / uploaded_file.name
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "wb") as f: 
            f.write(uploaded_file.getbuffer())

        with st.status("Protocollo RGD-Alpha in corso...") as status:
            ingestor = IngestoreDati()
            lista_asset = ingestor.elabora_csv(str(path), azienda)
            
            if lista_asset:
                engine = DataGateway()
                db.registra_caricamento(user_id, "UNIVERSAL", uploaded_file.name)
                
                # Elaborazione core
                report_analisi = engine.esegui_scan_strategico(
                    lista_asset, 
                    "UNIVERSAL", 
                    user_id=user_id, # <--- AGGIUNGI QUESTO!
                    fattore_stress=f_stress, 
                    weights=(w1, w2)
                )

                # ==========================================
                #   --- 5 KPI ALPHA (STRATEGIC VIEW) ---
                # ==========================================
                st.header("🛡️ Indicatori Strategici Vitali")
                
                # Pre-calcolo delle metriche per pulizia del codice
                avg_m = sum([a.get('trend_90gg', 0) for a in report_analisi]) / len(report_analisi) if report_analisi else 0
                resilience_score = max(round(100 - (f_stress * 10), 1), 0)
                
                # Creazione del layout a 5 colonne
                cols = st.columns(5)
                
                # 1. Solidità Aziendale
                cols[0].metric(
                    label="Solidità", 
                    value=f"{kpi_reali.get('solidita', 0)}%"
                )
                
                # 2. Indice di Rischio Medio
                cols[1].metric(
                    label="Rischio Medio", 
                    value=f"{kpi_reali.get('rischio_medio', 0)}/10"
                )
                
                # 3. Trend Momentum (con logica colore dinamica)
                # Nota: delta_color="inverse" mette in rosso l'incremento del rischio (Accelerazione)
                cols[2].metric(
                    label="Trend Momentum", 
                    value=f"{round(avg_m, 2)}", 
                    delta="Accelerazione" if avg_m > 1.2 else "Stabile",
                    delta_color="inverse" if avg_m > 1.2 else "normal"
                )
                
                # 4. Efficienza Operativa
                cols[3].metric(
                    label="Efficienza Risorse", 
                    value="84.2%"
                )
                
                # 5. Resilience (Impatto Stress Test)
                cols[4].metric(
                    label="Resilience", 
                    value=f"{resilience_score}%",
                    delta=f"-{(f_stress-1)*100:.0f}% Stress" if f_stress > 1 else None,
                    delta_color="inverse"
                )

                # --- GRAFICO MOMENTUM ---
                st.subheader("📈 Accelerazione del Rischio (Algoritmo EMA)")
                df_plot = pd.DataFrame(report_analisi)
                fig = px.bar(
                    df_plot, 
                    x="asset", 
                    y="trend_90gg",
                    color="stato",
                    color_discrete_map={"CRITICO": "#ff5f56", "ATTENZIONE": "#ffbd2e", "OTTIMALE": "#27c93f"}
                )

                # --- RAGIONAMENTO IA ---
                st.subheader("🧠 Ragionamento Strategico")
                st.markdown(f"""
                <div class="ai-reasoning">
                    <strong>SINTESI DIREZIONALE:</strong><br>
                    Il sistema rileva un impatto di crisi simulata che riduce la resilienza al {resilience_score}%. 
                    Il Momentum Score indica che il rischio non è statico ma in espansione temporale.<br><br>
                    <strong>AZIONE ALPHA:</strong><br>
                    Si suggerisce di dare priorità agli asset con Momentum > 1.5. Il tempo di giacenza sta erodendo 
                    il margine operativo più velocemente del previsto. Intervenire sulla supply chain entro 15gg.
                </div>
                """, unsafe_allow_html=True)

                # --- DETTAGLIO ASSET (VERSIONE CORRETTA E COMPLETA) ---
                st.subheader("📝 Piano d'Azione per Asset")
                for asset in report_analisi:
                    r = asset.get('rischio', 0)
                    # Usiamo i nomi che il motore effettivamente produce:
                    m = asset.get('trend_90gg', 0)
                    advice = asset.get('segnalazioni', 'Nessun consiglio disponibile')
                    
                    box = "kpi-box-critical" if r > 7 else "kpi-box"
                    st.markdown(f"""
                    <div class="{box}">
                        <b>{asset.get('asset')}</b> | Rischio: {r} | Trend Momentum: {m}
                        <br><small>🎯 <b>IA ADVICE:</b> {advice}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("Il file caricato non contiene asset validi da analizzare.")

# ==========================================
#   NAVIGAZIONE PAGINE (ADMIN & ARCHIVIO)
# ==========================================

elif scelta == "🕵️ Centrale Admin":
    st.title("🕵️ Centrale Admin | Supervisione Globale")
    st.write("Benvenuto nel centro di controllo. Qui puoi monitorare tutti gli utenti e le attività del sistema.")

    # 1. METRICHE DI SISTEMA (Recupero dati globali)
    df_utenti = db.supervisione_admin_metriche_globali()
    df_attivita = db.recupera_attivita_globale()
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Utenti Totali", len(df_utenti))
    col_b.metric("Analisi Eseguite", len(df_attivita))
    col_c.metric("Stato Database", "OPERATIVO", delta="Ottimale")

    st.divider()

    # 2. TABELLA UTENTI REGISTRATI
    st.subheader("👥 Utenti Registrati")
    if not df_utenti.empty:
        df_utenti_display = df_utenti.copy()
        if 'data_creazione' in df_utenti_display.columns:
            df_utenti_display['data_creazione'] = pd.to_datetime(df_utenti_display['data_creazione']).dt.strftime('%d/%m/%Y')
        st.dataframe(df_utenti_display, use_container_width=True)
    else:
        st.info("Nessun utente registrato nel sistema.")

    # 3. LOG ATTIVITÀ GLOBALE
    st.subheader("📊 Attività Recente nel Sistema")
    if not df_attivita.empty:
        st.dataframe(df_attivita.head(10), use_container_width=True)
    else:
        st.info("Nessuna attività registrata nelle ultime 24 ore.")

elif scelta == "📜 Archivio Storico":
    st.title("📜 Archivio Storico Analisi")
    st.write("Qui puoi consultare la cronologia delle tue attività e dei file elaborati.")

    # Recupera i dati dal database tramite l'istanza db
    df_storia = db.recupera_storia_caricamenti(user_id)

    if not df_storia.empty:
        df_display = df_storia[['timestamp', 'nome_file', 'contesto']].copy()
        df_display.columns = ['Data e Ora', 'File Elaborato', 'Tipo Analisi']
        df_display['Data e Ora'] = pd.to_datetime(df_display['Data e Ora']).dt.strftime('%d/%m/%Y %H:%M')
        st.dataframe(df_display, use_container_width=True)
        st.info(f"💡 Hai effettuato un totale di {len(df_display)} analisi strategiche.")
    else:
        st.info("Non ci sono ancora analisi registrate nel tuo archivio.")
        st.image("https://cdn-icons-png.flaticon.com/512/4076/4076432.png", width=80)