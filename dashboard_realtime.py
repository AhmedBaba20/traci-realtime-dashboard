import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

URL = "https://traci.tn/if3/ad/listing_ox.php?id_chauffeur=700042&max=200"
OUTPUT_FILE = "donnees_capteurs.csv"
MAX_HISTORY_HOURS = 24  # heures

st.set_page_config(page_title="Dashboard Temps Réel", layout="wide")
st.title("📊 Dashboard Temps Réel - Capteurs TRACI")

def scrape_data():
    options = Options()
    options.add_argument("--headless=new")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        rows = driver.find_elements(By.TAG_NAME, "tr")
        data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 24:
                heure = cols[2].text.strip()
                date = cols[10].text.strip()
                temp = cols[20].text.strip()
                humid = cols[21].text.strip()
                oxy = cols[22].text.strip()
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
    finally:
        driver.quit()
    return data

if st.button("🔄 Mettre à jour les données"):
    new_data = scrape_data()
    if new_data:
        if not os.path.exists(OUTPUT_FILE):
            pd.DataFrame(columns=["timestamp", "temperature", "humidity", "oxygen"]).to_csv(OUTPUT_FILE, index=False)

        df_existing = pd.read_csv(OUTPUT_FILE, parse_dates=["timestamp"])
        df_new = pd.DataFrame(new_data, columns=["timestamp", "temperature", "humidity", "oxygen"])
        df_new["timestamp"] = pd.to_datetime(df_new["timestamp"])

        df_all = pd.concat([df_existing, df_new]).drop_duplicates(subset=["timestamp"])
        cutoff = datetime.now() - timedelta(hours=MAX_HISTORY_HOURS)
        df_all = df_all[df_all["timestamp"] >= cutoff]

        df_all.to_csv(OUTPUT_FILE, index=False)
        st.success("Données mises à jour.")

if os.path.exists(OUTPUT_FILE):
    df_all = pd.read_csv(OUTPUT_FILE, parse_dates=["timestamp"])
    capteur = st.sidebar.selectbox("Capteur :", ["temperature", "humidity", "oxygen"])
    fig = px.line(df_all, x="timestamp", y=capteur, title=f"Évolution de {capteur} (dernières 24h)")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_all.tail(10))

