
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Bankroll Tracker", layout="centered", initial_sidebar_state="collapsed")

# 1. Connexion à Google Sheets via le Cloud (Streamlit Secrets)
@st.cache_resource
def connect_to_gsheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # On lit directement les identifiants depuis le cloud, plus besoin de fichier local !
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

try:
    gc = connect_to_gsheets()
    NOM_DU_FICHIER_GSHEETS = "Tracker Paris" # REMPLACEZ PAR VOTRE NOM DE FICHIER SI DIFFERENT
    sheet = gc.open(NOM_DU_FICHIER_GSHEETS).sheet1
except Exception as e:
    st.error("Erreur de connexion à Google Sheets. Vérifiez les secrets Streamlit.")
    st.stop()

# 2. Récupération des données
def load_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    for col in ['Mise', 'Gain', 'Bénéfice', 'Cote']:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace(',', '.').astype(float)
    return df

df = load_data()

st.markdown('''
<style>
    .metric-card { background-color: #1E2130; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 10px; }
    .metric-label { color: #8C92AC; font-size: 12px; text-transform: uppercase; }
    .metric-positive { color: #00E676; font-size: 24px; font-weight: bold; }
    .metric-neutral { color: #FFFFFF; font-size: 24px; font-weight: bold; }
</style>
''', unsafe_allow_html=True)

menu = st.selectbox("Menu", ["🏠 Home", "➕ Ajouter un pari"], label_visibility="collapsed")

if menu == "🏠 Home":
    st.markdown("### 📈 Dashboard")
    if not df.empty and 'Bénéfice' in df.columns:
        benefice_total = df['Bénéfice'].sum()
        mises_totales = df['Mise'].sum()
        roi = (benefice_total / mises_totales * 100) if mises_totales > 0 else 0

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">PARIS</div><div class="metric-neutral">{len(df)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-card"><div class="metric-label">ROI</div><div class="metric-positive">{roi:.2f}%</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">BÉNÉFICE</div><div class="metric-positive">{benefice_total:.2f}€</div></div>', unsafe_allow_html=True)
        st.dataframe(df.tail(5))
    else:
        st.info("Aucune donnée ou colonnes manquantes.")

elif menu == "➕ Ajouter un pari":
    st.markdown("### ➕ Nouveau Pari")
    with st.form("form_ajout"):
        intitule = st.text_input("Intitulé")
        mise = st.number_input("Mise (€)", min_value=0.0, format="%.2f")
        cote = st.number_input("Cote", min_value=1.01, format="%.2f")
        etat = st.selectbox("État", ["En attente", "Gagné", "Perdu"])
        submit = st.form_submit_button("Ajouter à Google Sheets")

        if submit:
            benef = (mise * cote) - mise if etat == "Gagné" else (-mise if etat == "Perdu" else 0)
            new_row = [
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Simple", "Football", intitule, cote, mise,
                (mise * cote) if etat == "Gagné" else 0, benef, etat, "Betclic"
            ]
            sheet.append_row(new_row)
            st.success("Pari ajouté avec succès ! ✅")
            st.cache_resource.clear()
