import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px

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

# Google Sheet öffnen per Sheet-ID (nur ID, keine URL)
SHEET_ID = "1QdIWos3OGLbeL-0LD3hUaVjcMs4vZj3XH6YHY6tdhZk"
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
    st.header("Depotentwicklung über Zeit")

    # Daten laden
    rows = sheet.get_all_records()
    df = pd.DataFrame(rows)

    df["Einzahlungen Total (CHF)"] = pd.to_numeric(df["Einzahlungen Total (CHF)"])
    df["Kontostand Total (CHF)"] = pd.to_numeric(df["Kontostand Total (CHF)"])
    df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%Y")

    # Sortieren nach Datum
    df = df.sort_values(by="Datum")
    df["Quartal"] = df["Datum"].dt.to_period("Q").astype(str)

    # Chart
    fig = px.line(
        df,
        x="Datum",
        y="Kontostand Total (CHF)",
        color="Depot",
        markers=True,
    )

    fig.update_layout(
        xaxis=dict(tickformat="%Y-%m", title="Datum"),
        yaxis_title="Depotwert",
        title="",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    # KPIs
    st.subheader("Kennzahlen pro Depot")

    for depot in df["Depot"].unique():
        df_depot = df[df["Depot"] == depot].sort_values("Datum")

        # Einzahlung je Zeile berechnen
        df_depot["Einzahlung pro Zeile"] = df_depot["Einzahlungen Total (CHF)"].diff().fillna(df_depot["Einzahlungen Total (CHF)"])

        # Zeitgewichtete Rendite berechnen
        renditefaktoren = []
        for i in range(1, len(df_depot)):
            start = df_depot.iloc[i - 1]
            end = df_depot.iloc[i]

            # Kapitalwert zu Beginn des Zeitraums (inkl. neuer Einzahlung)
            kapital_anfang = start["Kontostand Total (CHF)"] + end["Einzahlung pro Zeile"]
            kapital_ende = end["Kontostand Total (CHF)"]

            if kapital_anfang > 0:
                faktor = kapital_ende / kapital_anfang
                renditefaktoren.append(faktor)

        # Gesamtrendite (zeitgewichtet)
        if renditefaktoren:
            twr = 1
            for f in renditefaktoren:
                twr *= f
            rendite_total = twr - 1
        else:
            rendite_total = 0.0

        # Annualisierte Rendite berechnen
        tage = (df_depot["Datum"].iloc[-1] - df_depot["Datum"].iloc[0]).days
        jahre = tage / 365.25 if tage > 0 else 1

        rendite_p_a = (1 + rendite_total) ** (1 / jahre) - 1 if jahre > 0 else 0

        # Aktueller Stand
        letzter_kontostand = df_depot["Kontostand Total (CHF)"].iloc[-1]
        einzahlungen_total = df_depot["Einzahlungen Total (CHF)"].iloc[-1]

        st.markdown(f"### {depot}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Einzahlungen", f"CHF {einzahlungen_total:,.0f}")
        col2.metric("Letzter Stand", f"CHF {letzter_kontostand:,.0f}")
        col3.metric("Rendite total (TWR)", f"{rendite_total*100:.2f}%")
        col4.metric("Rendite p.a. (TWR)", f"{rendite_p_a*100:.2f}%")
