import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import altair as alt

# Google Sheets API Scope
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Service-Account-Daten aus secrets holen
service_account_info = st.secrets["gcp_service_account"]

credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(credentials)

# Google Sheet öffnen per Sheet-ID
SHEET_ID = "https://docs.google.com/spreadsheets/d/1QdIWos3OGLbeL-0LD3hUaVjcMs4vZj3XH6YHY6tdhZk/edit?gid=0#gid=0"
sheet = client.open_by_key(SHEET_ID).sheet1

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
    st.header("Entwicklung & Kennzahlen")

    # Daten aus Google Sheet laden
    rows = sheet.get_all_records()
    df = pd.DataFrame(rows)

    # String-Werte in Zahlen umwandeln
    df["Einzahlungen Total (CHF)"] = df["Einzahlungen Total (CHF)"].replace("CHF ", "", regex=True).replace(".", "", regex=True).replace(",", ".", regex=True).astype(float)
    df["Kontostand Total (CHF)"] = df["Kontostand Total (CHF)"].replace("CHF ", "", regex=True).replace(".", "", regex=True).replace(",", ".", regex=True).astype(float)

    # Datum parsen
    df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%Y")

    # Quartal extrahieren
    df["Jahr"] = df["Datum"].dt.year
    df["Quartal"] = df["Datum"].dt.to_period("Q")
    df["Quartal_kurz"] = df["Quartal"].apply(lambda x: f"Q{x.quarter}/{str(x.year)[2:]}")

    # Sortierte Quartale
    quartale_sort = sorted(df["Quartal_kurz"].unique(), key=lambda x: (int(x.split("/")[1]), int(x[1])))

    # KPI-Berechnung
    st.subheader("Kennzahlen pro Depot")
    for depot in df["Depot"].unique():
        df_depot = df[df["Depot"] == depot].sort_values("Datum")

        letzter_kontostand = df_depot["Kontostand Total (CHF)"].iloc[-1]
        einzahlungen_total = df_depot["Einzahlungen Total (CHF)"].iloc[-1]

        if einzahlungen_total > 0:
            rendite_total = (letzter_kontostand - einzahlungen_total) / einzahlungen_total
        else:
            rendite_total = 0.0

        tage = (df_depot["Datum"].iloc[-1] - df_depot["Datum"].iloc[0]).days
        if tage > 0 and einzahlungen_total > 0:
            jahre = tage / 365
            rendite_p_a = ((letzter_kontostand / einzahlungen_total) ** (1 / jahre)) - 1
        else:
            rendite_p_a = 0.0

        st.markdown(f"### {depot}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Einzahlungen", f"CHF {einzahlungen_total:,.0f}")
        col2.metric("Letzter Stand", f"CHF {letzter_kontostand:,.0f}")
        col3.metric("Rendite total", f"{rendite_total*100:.2f}%")
        col4.metric("Rendite p.a.", f"{rendite_p_a*100:.2f}%")

    # Chart: Entwicklung pro Depot pro Quartal
    st.subheader("Depotentwicklung pro Quartal")

    df_q = df.copy()
    df_q_grouped = df_q.groupby(["Depot", "Quartal_kurz"])["Kontostand Total (CHF)"].last().reset_index()

    # Invertierte Y-Achse durch Umwandlung in negatives Wachstum
    fig = px.line(
        df_q_grouped,
        x="Quartal_kurz",
        y="Kontostand Total (CHF)",
        color="Depot",
        markers=True
    )

    # Sortierte Achsenbeschriftung
    fig.update_xaxes(categoryorder="array", categoryarray=quartale_sort)
    fig.update_yaxes(title="Kontostand (CHF)")  # Y-Achse invertiert
    fig.update_layout(height=500)

    st.plotly_chart(fig, use_container_width=True)
bar.")

