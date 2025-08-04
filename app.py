import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Secrets auslesen
secrets = st.secrets

credentials_dict = {
    "type": secrets["type"],
    "project_id": secrets["project_id"],
    "private_key_id": secrets["private_key_id"],
    "private_key": secrets["private_key"],
    "client_email": secrets["client_email"],
    "client_id": secrets["client_id"],
    "auth_uri": secrets["auth_uri"],
    "token_uri": secrets["token_uri"],
    "auth_provider_x509_cert_url": secrets["auth_provider_x509_cert_url"],
    "client_x509_cert_url": secrets["client_x509_cert_url"],
}

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)

# Google Sheet öffnen
SHEET_NAME = "Depot Tracker"  # <- Passe ggf. an den Namen deines Sheets an
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
        datum_str = datum.strftime("%d.%m.%Y")
        sheet.append_row([depot, datum_str, einzahlungen, kontostand])
        st.success("Eintrag erfolgreich gespeichert!")
