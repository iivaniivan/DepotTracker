import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import altair as alt

# --- Google Sheets API Setup ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Service Account Credentials aus streamlit secrets laden
service_account_info = st.secrets["gcp_service_account"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(credentials)

# Sheet ID aus deiner URL extrahiert
SHEET_ID = "1QdIWos3OGLbeL-0LD3hUaVjcMs4vZj3XH6YHY6tdhZk"
sheet = client.open_by_key(SHEET_ID).sheet1

# Tabs anlegen
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
            datum_str = datum.strftime("%d.%m.%Y")
            # Daten als neue Zeile in Google Sheet anhängen
            sheet.append_row([depot, datum_str, einzahlungen, kontostand])
            st.success("Eintrag erfolgreich gespeichert!")

with tab2:
    st.header("Entwicklung & Kennzahlen")

    # Daten aus Google Sheet holen
    rows = sheet.get_all_records()
    df = pd.DataFrame(rows)

    if df.empty:
        st.warning("Keine Daten im Google Sheet gefunden.")
    else:
        # Falls Spalten noch Währungsformat als Text enthalten (CHF, Tausenderpunkte),
        # diese Zeile anpassen oder entfernen, falls bereits numerisch:
        # Beispiel Entfernen von 'CHF ' und Umwandlung deutscher Zahlenformate
        for col in ["Einzahlungen Total (CHF)", "Kontostand Total (CHF)"]:
            if df[col].dtype == object:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace("CHF ", "", regex=False)
                    .str.replace("'", "", regex=False)  # evtl Tausender-Apostroph entfernen
                    .str.replace(".", "", regex=False)  # Punkte Tausender entfernen
                    .str.replace(",", ".", regex=False)  # Komma in Dezimalpunkt umwandeln
                    .astype(float)
                )

        # Datum in datetime umwandeln
        df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%Y")

        # Quartal extrahieren
        df["Jahr"] = df["Datum"].dt.year
        df["Quartal"] = df["Datum"].dt.to_period("Q")
        df["Quartal_kurz"] = df["Quartal"].apply(lambda x: f"Q{x.quarter}/{str(x.year)[2:]}")

        # Quartale sortieren nach Jahr und Quartal
        quartale_sort = sorted(df["Quartal_kurz"].unique(), key=lambda x: (int(x.split("/")[1]), int(x[1])))

        # KPIs je Depot
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
        df_q_grouped = (
            df_q.groupby(["Depot", "Quartal_kurz"])["Kontostand Total (CHF)"]
            .last()
            .reset_index()
        )

        # Altair Chart (Performance-Chart von unten links nach oben rechts)
        chart = (
            alt.Chart(df_q_grouped)
            .mark_line(point=True)
            .encode(
                x=alt.X("Quartal_kurz:N", sort=quartale_sort, title="Quartal"),
                y=alt.Y("Kontostand Total (CHF):Q", title="Kontostand (CHF)"),
                color="Depot:N",
                tooltip=["Depot", "Quartal_kurz", alt.Tooltip("Kontostand Total (CHF)", format=".2f")],
            )
            .properties(width=700, height=400)
        )

        st.altair_chart(chart, use_container_width=True)
