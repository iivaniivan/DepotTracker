import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px

# Einfacher Passwortschutz
def check_login():
    st.sidebar.title("🔒 Login erforderlich")
    username = st.sidebar.text_input("Benutzername")
    password = st.sidebar.text_input("Passwort", type="password")

    if username == "Yvan" and password == "Depot2025":
        return True
    else:
        st.sidebar.warning("Bitte Benutzername und Passwort eingeben.")
        st.stop()

# Login prüfen, bevor App geladen wird
check_login()

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
    df.columns = df.columns.str.strip()


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

    # KPIs als Tabelle
    st.subheader("Kennzahlen pro Depot")

    # Datenstruktur für alle Depots
    kpi_list = []

    for depot in df["Depot"].unique():
        df_depot = df[df["Depot"] == depot].sort_values("Datum")

        # Einzahlung je Zeile berechnen
        df_depot["Einzahlung pro Zeile"] = df_depot["Einzahlungen Total (CHF)"].diff().fillna(df_depot["Einzahlungen Total (CHF)"])

        # Zeitgewichtete Rendite berechnen (TWR)
        renditefaktoren = []
        for i in range(1, len(df_depot)):
            start = df_depot.iloc[i - 1]
            end = df_depot.iloc[i]

            kapital_anfang = start["Kontostand Total (CHF)"] + end["Einzahlung pro Zeile"]
            kapital_ende = end["Kontostand Total (CHF)"]

            if kapital_anfang > 0:
                faktor = kapital_ende / kapital_anfang
                renditefaktoren.append(faktor)

        if renditefaktoren:
            twr = 1
            for f in renditefaktoren:
                twr *= f
            rendite_total = twr - 1
        else:
            rendite_total = 0.0

        # Annualisierte Rendite (TWR p.a.)
        tage = (df_depot["Datum"].iloc[-1] - df_depot["Datum"].iloc[0]).days
        jahre = tage / 365.25 if tage > 0 else 1
        rendite_p_a = (1 + rendite_total) ** (1 / jahre) - 1 if jahre > 0 else 0

        # Einfache Rendite
        letzter_kontostand = df_depot["Kontostand Total (CHF)"].iloc[-1]
        einzahlungen_total = df_depot["Einzahlungen Total (CHF)"].iloc[-1]
        rendite_einfach = (letzter_kontostand - einzahlungen_total) / einzahlungen_total if einzahlungen_total > 0 else 0

        # In Liste speichern
        kpi_list.append({
            "Depot": depot,
            "Einzahlungen (CHF)": einzahlungen_total,
            "Letzter Stand (CHF)": letzter_kontostand,
            "Einfache Rendite (%)": rendite_einfach * 100,
            "Rendite total (TWR) (%)": rendite_total * 100,
            "Rendite p.a. (TWR) (%)": rendite_p_a * 100
        })

    # DataFrame aus Liste erzeugen
    df_kpi = pd.DataFrame(kpi_list)
    
    # Index bei 1 starten lassen
    df_kpi.index = df_kpi.index + 1

    # Tabelle anzeigen
    st.dataframe(df_kpi.style.format({...}), width=True)
    "Einzahlungen (CHF)": "{:,.0f}",
    "Letzter Stand (CHF)": "{:,.0f}",
    "Einfache Rendite (%)": "{:.2f}%",
    "Rendite total (TWR) (%)": "{:.2f}%",
    "Rendite p.a. (TWR) (%)": "{:.2f}%"
    }))
