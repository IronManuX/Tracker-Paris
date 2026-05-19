import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
from datetime import datetime
import json

st.set_page_config(page_title="Ma Bankroll", layout="centered", initial_sidebar_state="collapsed")

# --- 1. CONNEXION ROBUSTE ---
@st.cache_resource
def connect_to_gsheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["google_json"])
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)

try:
    gc = connect_to_gsheets()
    sheet = gc.open("Tracker Paris").sheet1 # Nom de votre fichier
except Exception as e:
    st.error("Erreur de connexion à Google Sheets.")
    st.stop()

def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    for col in ['Mise', 'Gain', 'Bénéfice', 'Cote']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace('€', '').str.strip(), errors='coerce').fillna(0)
    return df

df = load_data()

# --- 2. DESIGN (CSS) INSPIRÉ DE L'APPLI ---
st.markdown('''
<style>
    /* Fond de l'application */
    .stApp { background-color: #0B0E14; color: white; }
    
    /* Style des cartes de statistiques */
    .metric-card { 
        background-color: #1A1D29; 
        border-radius: 12px; 
        padding: 15px; 
        text-align: center; 
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-label { color: #8C92AC; font-size: 11px; text-transform: uppercase; font-weight: bold; letter-spacing: 1px;}
    .metric-value-blue { color: #4DA8DA; font-size: 24px; font-weight: bold; }
    .metric-value-green { color: #00E676; font-size: 24px; font-weight: bold; }
</style>
''', unsafe_allow_html=True)

# --- 3. NAVIGATION ---
menu = st.selectbox("Menu", ["🏠 Tableau de bord", "➕ Ajouter un pari", "📋 Historique"], label_visibility="collapsed")

if menu == "🏠 Tableau de bord":
    st.markdown("### Bankroll 2026")
    
    if not df.empty and 'Bénéfice' in df.columns:
        # Calculs
        benefice_total = df['Bénéfice'].sum()
        mises_totales = df['Mise'].sum()
        capital_depart = 376.79 # Modifiable
        
        roi = (benefice_total / mises_totales * 100) if mises_totales > 0 else 0
        progression = (benefice_total / capital_depart * 100)
        
        # Graphique de Bankroll (Courbe verte)
        df['Bénéfice Cumulé'] = df['Bénéfice'].cumsum()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index + 1, 
            y=df['Bénéfice Cumulé'],
            mode='lines',
            fill='tozeroy',
            fillcolor='rgba(0, 230, 118, 0.1)', # Vert transparent en dessous
            line=dict(color='#00E676', width=3)   # Ligne vert vif
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=10, b=10),
            height=250,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=True, gridcolor='#1A1D29', tickformat="€", side='left')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # Les 4 blocs de statistiques
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">PARIS</div><div class="metric-value-blue">{len(df)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-card"><div class="metric-label">ROI</div><div class="metric-value-green">{roi:.2f}%</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">BÉNÉFICE</div><div class="metric-value-green">{benefice_total:.2f}€</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-card"><div class="metric-label">PROGRESSION</div><div class="metric-value-green">{progression:.2f}%</div></div>', unsafe_allow_html=True)
            
    else:
        st.info("Aucune donnée trouvée.")

elif menu == "➕ Ajouter un pari":
    st.markdown("### ➕ Nouveau Pari")
    with st.form("form_ajout"):
        intitule = st.text_input("Intitulé (ex: Real Madrid - Bayern)")
        cote = st.number_input("Cote", min_value=1.01, format="%.2f")
        mise = st.number_input("Mise (€)", min_value=0.0, format="%.2f")
        etat = st.selectbox("État", ["En attente", "Gagné", "Perdu", "Remboursé"])
        bookmaker = st.selectbox("Bookmaker", ["Betclic", "Winamax", "Unibet", "ParionsSport"])
        submit = st.form_submit_button("Ajouter le pari", use_container_width=True)
        
        if submit:
            benef = (mise * cote) - mise if etat == "Gagné" else (-mise if etat == "Perdu" else 0)
            new_row = [
                datetime.now().strftime("%d/%m/%Y %H:%M"), "Simple", "Football", 
                intitule, cote, mise, (mise * cote) if etat == "Gagné" else 0, 
                benef, etat, bookmaker
            ]
            sheet.append_row(new_row)
            st.success("Pari ajouté avec succès ! ✅")
            st.cache_resource.clear()

elif menu == "📋 Historique":
    st.markdown("### 📋 Historique des Paris")
    st.dataframe(df[['Date', 'Intitulé du pari', 'Cote', 'Mise', 'Bénéfice', 'Etat']].iloc[::-1], use_container_width=True)
    
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
