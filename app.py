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

# Service-Account-Daten aus secrets holen
service_account_info = st.secrets["gcp_service_account"]

credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(credentials)

# Google Sheet öffnen per Sheet-ID
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
    st.title("Depot Tracker Übersicht")

    records = sheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        df = df.sort_values(by="Datum", ascending=True)
        
        # Datum in datetime konvertieren
        df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%Y")
        
        # Auswahl Depot für Chart
        depots_unique = df["Depot"].unique()
        selected_depots = st.multiselect("Depot auswählen für Chart", depots_unique, default=depots_unique.tolist())
        
        if selected_depots:
            df_chart = df[df["Depot"].isin(selected_depots)]
            # Pivot für Linienchart: Index=Datum, Spalten=Depot, Werte=Kontostand
            df_pivot = df_chart.pivot(index="Datum", columns="Depot", values="Kontostand Total (CHF)")
            
            st.line_chart(df_pivot)
        
        st.markdown("---")
        st.header("KPIs pro Depot")
        
        for depot in depots_unique:
            df_depot = df[df["Depot"] == depot].sort_values(by="Datum")
            
            einzahlungen_total = df_depot["Einzahlungen Total (CHF)"].sum()
            letzter_kontostand = df_depot["Kontostand Total (CHF)"].iloc[-1]
            erstes_datum = df_depot["Datum"].iloc[0]
            letztes_datum = df_depot["Datum"].iloc[-1]
            jahre = (letztes_datum - erstes_datum).days / 365.25
            
            rendite_total = (letzter_kontostand - einzahlungen_total) / einzahlungen_total if einzahlungen_total > 0 else 0
            rendite_p_a = (1 + rendite_total) ** (1 / jahre) - 1 if jahre > 0 else 0
            
            st.subheader(depot)
            st.write(f"**Letzter Kontostand:** CHF {letzter_kontostand:,.2f}")
            st.write(f"**Total Einzahlungen:** CHF {einzahlungen_total:,.2f}")
            st.write(f"**Rendite total:** {rendite_total*100:.2f} %")
            st.write(f"**Rendite p.a.:** {rendite_p_a*100:.2f} %")
            st.write(f"**Erster Eintrag:** {erstes_datum.date()}")
            st.write(f"**Letzter Eintrag:** {letztes_datum.date()}")
            st.markdown("---")
            
    else:
        st.info("Noch keine Einträge vorhanden.")
