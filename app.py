import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets API Scope
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Komplette Service-Account-Daten aus secrets holen
service_account_info = st.secrets["gcp_service_account"]

credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(credentials)

# Google Sheet öffnen
SHEET_ID = "1QdIWos3OGLbeL-0LD3hUaVjcMs4vZj3XH6YHY6tdhZk"
sheet = client.open_by_key(SHEET_ID).sheet1

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
        datum_str = datum.strftime("%d.%m.%Y")  # z.B. 04.08.2025

        # Neue Zeile in Google Sheet schreiben
        sheet.append_row([depot, datum_str, einzahlungen, kontostand])
        st.success("Eintrag erfolgreich gespeichert!")

import pandas as pd

import pandas as pd  # Falls noch nicht importiert, ganz oben hinzufügen

# Alle Daten aus dem Sheet laden
records = sheet.get_all_records()
if records:
    df = pd.DataFrame(records)

    # Neuste zuerst und alten Index als Spalte behalten
    df = df.sort_values(by="Datum", ascending=False).reset_index()

    # Nur die letzten 5 Einträge
    latest_entries = df.head(5)

    # Tabelle mit Lösch-Buttons
    for i, row in latest_entries.iterrows():
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(f"**{row['Depot']}** am {row['Datum']} – Einzahlung: CHF {row['Einzahlungen Total (CHF)']}, Kontostand: CHF {row['Kontostand Total (CHF)']}")
        with col2:
            if st.button("Löschen", key=f"delete_{i}"):
                original_index = row['index']  # Index im Original DataFrame (ungefiltert, ungesortiert)
                sheet.delete_rows(original_index + 2)  # +2 wegen Header und 0-basierendem Index
                st.success("Eintrag gelöscht. Bitte Seite neu laden.")
                st.stop()
else:
    st.info("Noch keine Einträge vorhanden.")


