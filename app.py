import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Google Sheets Setup
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("depottracker-key.json", scopes=SCOPE)
client = gspread.authorize(creds)

# Google Sheet öffnen
SHEET_NAME = "Depot Tracker"  # <- passe an deinen Sheet-Namen an
sheet = client.open(SHEET_NAME).sheet1

# Streamlit UI
st.title("Depot Tracker")
st.write("Willkommen zu deinem Depot-Tracker!")

depots = [
    "3a Yvan – VZ",
    "3a Yvan – Finpension",
    "3a Vanessa - Frankly",
    "ETF Yvan – VZ",
    "ETF Yvan - True Wealth"
]

with st.form(key="depot_form"):
    depot = st.selectbox("Depot auswählen", depots)
    datum = st.date_input("Datum auswählen")
    einzahlungen = st.number_input("Einzahlungen Total (CHF)", min_value=0.0, format="%.2f")
    kontostand = st.number_input("Kontostand Total (CHF)", min_value=0.0, format="%.2f")
    
    submit_button = st.form_submit_button(label="Eintrag speichern")

    if submit_button:
        datum_str = datum.strftime("%d.%m.%Y")  # z. B. 04.08.2025

        # Neue Zeile in Google Sheet schreiben
        sheet.append_row([depot, datum_str, einzahlungen, kontostand])
        st.success("Eintrag erfolgreich gespeichert!")
