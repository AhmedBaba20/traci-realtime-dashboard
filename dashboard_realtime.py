import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import requests
from bs4 import BeautifulSoup

# -------------------------
# CONFIG
# -------------------------
URL = "https://traci.tn/if3/ad/listing_ox.php?id_chauffeur=700042&max=200"
OUTPUT_FILE = "donnees_capteurs.csv"
MAX_HISTORY_HOURS = 24  # heures

st.set_page_config(page_title="Dashboard Temps Réel", layout="wide")
st.title("📊 Dashboard Temps Réel - Capteurs TRACI")

# -------------------------
# SCRAPING FUNCTION (No Selenium)
# -------------------------
def scrape_data():
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.find_all("tr")
    data = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 24:
            heure = cols[2].get_text(strip=True)
            date = cols[10].get_text(strip=True)
            temp = cols[20].get_text(strip=True)
            humid = cols[21].get_text(strip=True)
            oxy = cols[22].get_text(strip=True)

            try:
                dt_obj = datetime.strptime(date + heure, "%d%m%y%H%M%S")
                timestamp = dt_obj.isoformat()
                data.append([
                    timestamp,
                    float(temp) if temp else None,
                    float(humid) if humid else None,
                    float(oxy) if oxy else None
                ])
            except ValueError:
                continue
    return data

# -------------------------
# UPDATE DATA BUTTON
# -------------------------
if st.button("🔄 Mettre à jour les données"):
    new_data = scrape_data()
    if new_data:
        if not os.path.exists(OUTPUT_FILE):
            pd.DataFrame(columns=["timestamp", "temperature", "humidity", "oxygen"]).to_csv(OUTPUT_FILE, index=False)

        df_existing = pd.read_csv(OUTPUT_FILE, parse_dates=["timestamp"])
        df_new = pd.DataFrame(new_data, columns=["timestamp", "temperature", "humidity", "oxygen"])
        df_new["timestamp"] = pd.to_datetime(df_new["timestamp"])

        # Merge and keep only last 24h
        df_all = pd.concat([df_existing, df_new]).drop_duplicates(subset=["timestamp"])
        cutoff = datetime.now() - timedelta(hours=MAX_HISTORY_HOURS)
        df_all = df_all[df_all["timestamp"] >= cutoff]

        df_all.to_csv(OUTPUT_FILE, index=False)
        st.success("Données mises à jour.")

# -------------------------
# DISPLAY DATA & CHART
# -------------------------
if os.path.exists(OUTPUT_FILE):
    df_all = pd.read_csv(OUTPUT_FILE, parse_dates=["timestamp"])
    if not df_all.empty:
        capteur = st.sidebar.selectbox("Capteur :", ["temperature", "humidity", "oxygen"])
        fig = px.line(df_all, x="timestamp", y=capteur, title=f"Évolution de {capteur} (dernières 24h)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_all.tail(10))
    else:
        st.warning("Aucune donnée disponible. Cliquez sur 'Mettre à jour les données'.")
