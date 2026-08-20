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

# Importiamo la logica centralizzata dal pacchetto auth
from auth.auth import inizializza_sessione, login_utente, logout_utente

# =========================
#   CONFIGURAZIONE BASE
# =========================
load_dotenv()
PROJECT_ROOT = Path(__file__).parent
DATA_ROOT = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_ROOT / "uploads"

for folder in [UPLOAD_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="RGD-Alpha | War Room Strategica",
    layout="wide",
    page_icon="🛡️"
)

inizializza_sessione()

# =========================
#   CSS ENTERPRISE POTENZIATO
# =========================
st.markdown("""
    <style>
    .kpi-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #007BFF; margin-bottom: 15px; }
    .kpi-box-critical { background-color: #fff5f5; padding: 20px; border-radius: 10px; border-left: 5px solid #dc3545; margin-bottom: 15px; }
    .ai-reasoning { background: #0e1117; border: 1px solid #d4af37; padding: 25px; border-radius: 15px; color: #e2e8f0; line-height: 1.6; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .crew-box { padding:15px; border-radius:10px; background:rgba(255,255,255,0.02); margin-bottom:10px; border-left: 5px solid #ccc; }
    </style>
""", unsafe_allow_html=True)

db = DatabaseAziendale()

# =========================
#   GESTIONE REGISTRAZIONE
# =========================
def registra_nuovo_utente(email: str, password: str, conferma: str):
    if not email or not password or not conferma:
        st.error("Compila tutti i campi.")
        return
    if password != conferma:
        st.error("Le password non coincidono.")
        return
    try:
        esistente = db.get_utente_by_email(email)
        if esistente:
            st.error("Email già registrata.")
            return
        
        # Genera l'hash sicuro della password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        ruolo = "admin" if email.lower() == "andrewdicenso@libero.it" else "user"
        user_id = db.crea_utente(email=email, password_hash=password_hash, ruolo=ruolo)
        if user_id:
            st.success("✅ Registrazione completata. Effettua il login.")
            st.balloons()
    except Exception as e:
        st.error(f"Errore registrazione: {e}")

# =========================
#   SCHERMATA AUTH
# =========================
if not st.session_state.autenticato:
    tab_login, tab_register = st.tabs(["🔐 Login", "🆕 Registrazione"])
    with tab_login:
        st.title("🔐 Accesso Utente")
        e_login = st.text_input("Email", key="l_email").strip()
        p_login = st.text_input("Password", type="password", key="l_pwd").strip()
        if st.button("Accedi"):
            if login_utente(db, e_login, p_login): st.rerun()
            else: st.error("Credenziali errate.")
    with tab_register:
        st.title("🆕 Crea account Beta")
        e_reg = st.text_input("Email", key="r_email").strip()
        p_reg = st.text_input("Password", type="password", key="r_pwd").strip()
        c_reg = st.text_input("Conferma", type="password", key="r_conf").strip()
        if st.button("Registrati"): registra_nuovo_utente(e_reg, p_reg, c_reg)
    st.stop()

# =========================
#   NAVIGAZIONE SIDEBAR
# =========================
user_id = st.session_state.user_id
azienda = st.session_state.azienda
ruolo = st.session_state.ruolo
is_admin = (ruolo == "admin")

st.sidebar.title("🛡️ RGD-ALPHA")
st.sidebar.write(f"Operatore: **{azienda}**")
menu = ["📊 War Room Strategica", "📜 Archivio Storico"]
if is_admin: menu.insert(0, "🕵️ Centrale Admin")
scelta = st.sidebar.radio("Navigazione", menu)

if st.sidebar.button("Logout"): logout_utente()

# =========================
#   WAR ROOM STRATEGICA
# =========================
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
        path = UPLOAD_DIR / azienda / uploaded_file.name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f: f.write(uploaded_file.getbuffer())

        with st.status("Protocollo RGD-Alpha in corso...") as status:
            ingestor = IngestoreDati()
            lista_asset = ingestor.elabora_csv(str(path), azienda)
            
            if lista_asset:
                engine = DataGateway()
                db.registra_caricamento(user_id, "UNIVERSAL", uploaded_file.name)
                # Calcolo con Stress Test e Pesi EMA
                report_analisi = engine.esegui_scan_strategico(lista_asset, "UNIVERSAL", fattore_stress=f_stress, weights=(w1, w2))
                kpi_reali = db.calcola_e_salva_kpi_correnti(user_id)
                status.update(label="Analisi Strategica Completata!", state="complete")

                # --- 5 KPI ALPHA ---
                st.header("🛡️ Indicatori Strategici Vitali")
                cols = st.columns(5)
                cols[0].metric("Solidità", f"{kpi_reali.get('solidita', 0)}%")
                cols[1].metric("Rischio Medio", f"{kpi_reali.get('rischio_medio', 0)}/10")
                avg_m = sum([a.get('momentum_score', 0) for a in report_analisi]) / len(report_analisi) if report_analisi else 0
                cols[2].metric("Trend Momentum", f"{round(avg_m, 2)}", delta="Accelerazione" if avg_m > 1.2 else "Stabile")
                cols[3].metric("Efficienza Risorse", "84.2%")
                res = max(round(100 - (f_stress * 10), 1), 0)
                cols[4].metric("Resilience", f"{res}%")

                # --- GRAFICO MOMENTUM ---
                st.subheader("📈 Accelerazione del Rischio (Algoritmo EMA)")
                df_plot = pd.DataFrame(report_analisi)
                fig = px.bar(df_plot, x="asset", y="momentum_score", color="stato",
                             color_discrete_map={"CRITICO": "#ff5f56", "ATTENZIONE": "#ffbd2e", "OTTIMALE": "#27c93f"})
                st.plotly_chart(fig, width='stretch')

                # --- RAGIONAMENTO IA ---
                st.subheader("🧠 Ragionamento Strategico")
                st.markdown(f"""
                <div class="ai-reasoning">
                    <strong>SINTESI DIREZIONALE:</strong><br>
                    Il sistema rileva un impatto di crisi simulata che riduce la resilienza al {res}%. 
                    Il Momentum Score indica che il rischio non è statico ma in espansione temporale.<br><br>
                    <strong>AZIONE ALPHA:</strong><br>
                    Si suggerisce di dare priorità agli asset con Momentum > 1.5. Il tempo di giacenza sta erodendo 
                    il margine operativo più velocemente del previsto. Intervenire sulla supply chain entro 15gg.
                </div>
                """, unsafe_allow_html=True)

                # --- DETTAGLIO ASSET ---
                st.subheader("📝 Piano d'Azione per Asset")
                for asset in report_analisi:
                    r = asset.get('rischio', 0)
                    box = "kpi-box-critical" if r > 7 else "kpi-box"
                    st.markdown(f"""
                    <div class="{box}">
                        <b>{asset.get('asset')}</b> | Rischio: {r} | Momentum: {asset.get('momentum_score')}
                        <br><small>🎯 <b>IA ADVICE:</b> {asset.get('consiglio_strategico')}</small>
                    </div>
                    """, unsafe_allow_html=True)

                # ========================================================
                # --- INTEGRAZIONE RGD-ALPHA CREW (NODE.JS BRIDGE) ---
                # ========================================================
                st.markdown("---")
                st.header("👥 RGD-ALPHA CREW | Client Risk Early Warning")
                
                try:
                    # Bridge simulato con il Backend Node.js
                    col_crew1, col_crew2, col_crew3 = st.columns(3)
                    with col_crew1: st.metric("Clienti Monitorati", "124")
                    with col_crew2: st.metric("Clienti ad Alto Rischio", "8", delta="↑ 2", delta_color="inverse")
                    with col_crew3: st.metric("Churn Rate Previsto", "3.2%")

                    st.subheader("🚨 Alert Recenti: Relazioni Clienti (da MongoDB)")
                    clienti_alert = [
                        {"cliente": "Azienda Meccanica SPA", "rischio": "ROSSO", "motivo": "Drop frequenza d'acquisto -40%"},
                        {"cliente": "Logistica Nord Srl", "rischio": "GIALLO", "motivo": "Peggioramento tono comunicazioni"},
                        {"cliente": "Distribuzione Alimentare", "rischio": "ROSSO", "motivo": "Ritardo pagamenti > 15gg"}
                    ]
                    for c in clienti_alert:
                        c_color = "#e74c3c" if c['rischio'] == "ROSSO" else "#f1c40f"
                        st.markdown(f"""
                            <div class="crew-box" style="border-left-color: {c_color};">
                                <strong>{c['cliente']}</strong> - <span style="color:{c_color}">{c['rischio']}</span><br>
                                <small>{c['motivo']}</small>
                            </div>
                        """, unsafe_allow_html=True)
                except:
                    st.info("⚠️ Collegamento al modulo CREW (Node.js) in corso di inizializzazione...")

# =========================
#   CENTRALE ADMIN
# =========================
if scelta == "🕵️ Centrale Admin" and is_admin:
    st.title("🕵️ Centrale Admin")
    try:
        df = db.supervisione_admin_metriche_globali()
        if df is not None and not df.empty:
                st.dataframe(df, width=None, hide_index=True)
    except: st.info("In attesa di dati dai nodi periferici.")

st.write(st.session_state)