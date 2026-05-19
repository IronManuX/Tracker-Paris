import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
from datetime import datetime
import json

st.set_page_config(page_title="Bankroll Tracker", layout="centered", initial_sidebar_state="collapsed")

# 1. Connexion à Google Sheets 
@st.cache_resource
def connect_to_gsheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Lecture de la clé secrète formatée pour éviter les erreurs TOML
    creds_dict = json.loads(st.secrets["google_json"])
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

try:
    gc = connect_to_gsheets()
    # Le nom exact de votre fichier Google Sheets avec l'espace
    NOM_DU_FICHIER_GSHEETS = "Tracker Paris" 
    sheet = gc.open(NOM_DU_FICHIER_GSHEETS).sheet1
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# 2. Récupération des données
def load_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Nouvelle méthode robuste de nettoyage
    for col in ['Mise', 'Gain', 'Bénéfice', 'Cote']:
        if col in df.columns:
            # On remplace les virgules, on enlève les espaces, et on convertit en nombre.
            # "coerce" permet de transformer les erreurs (comme une case vide) en 0
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace('€', '').str.strip(), errors='coerce').fillna(0)
    
    return df

df = load_data()

# Styles pour recréer l'aspect de l'application
st.markdown('''
<style>
    .metric-card { background-color: #1E2130; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 10px; }
    .metric-label { color: #8C92AC; font-size: 12px; text-transform: uppercase; }
    .metric-positive { color: #00E676; font-size: 24px; font-weight: bold; }
    .metric-neutral { color: #FFFFFF; font-size: 24px; font-weight: bold; }
</style>
''', unsafe_allow_html=True)

menu = st.selectbox("Menu Navigation", ["🏠 Home", "➕ Ajouter un pari"], label_visibility="collapsed")

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
        
        st.markdown("**Derniers paris :**")
        st.dataframe(df.tail(5))
    else:
        st.info("Aucune donnée trouvée ou colonnes manquantes dans Google Sheets.")

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
