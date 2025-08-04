import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Google Sheets API Scope
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Service-Account-Daten aus Streamlit-Secrets holen
service_account_info = st.secrets["gcp_service_account"]

credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(credentials)

# Google Sheet öffnen
SHEET_NAME = "DepotTracker Daten"
sheet = client.open(SHEET_NAME).sheet1

tab1, tab2 = st.tabs(["Eingabe", "Übersicht"])

with tab1:
    st.title("Depot Tracker Eingabe")
    
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
            datum_str = datum.strftime("%d.%m.%Y")  # z.B. 04.08.2025

            # Neue Zeile in Google Sheet schreiben
            sheet.append_row([depot, datum_str, einzahlungen, kontostand])
            st.success("Eintrag erfolgreich gespeichert!")

with tab2:
    st.title("Depot Tracker Übersicht")
    records = sheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        df = df.sort_values(by="Datum", ascending=False)
        
        st.write("Letzte 5 Einträge:")
        st.dataframe(df.head(5))
        
        # Beispiel Chart
        st.line_chart(df.head(10)[["Einzahlungen Total (CHF)", "Kontostand Total (CHF)"]])
    else:
        st.info("Noch keine Einträge vorhanden.")



