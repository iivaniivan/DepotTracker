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
    import numpy as np

    st.title("Depot Tracker Übersicht")

    records = sheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        df = df.sort_values(by="Datum", ascending=True)

        # Datum in datetime konvertieren
        df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%Y")

        # Auswahl Depot für Chart, standardmäßig alle
        depots_unique = df["Depot"].unique()
        selected_depots = st.multiselect(
            "Depot auswählen für Chart", depots_unique, default=depots_unique.tolist()
        )

        if selected_depots:
            df_chart = df[df["Depot"].isin(selected_depots)]

            # Pivot mit Aggregation max statt pivot (Dubletten-Problem)
            df_pivot = df_chart.pivot_table(
                index="Datum",
                columns="Depot",
                values="Kontostand Total (CHF)",
                aggfunc="max",
            ).fillna(method="ffill")  # Fehlende Werte nach vorne füllen (für bessere Linien)

            st.line_chart(df_pivot)

        st.markdown("---")
        st.header("KPIs pro Depot und Jahr")

        # Jahr extrahieren
        df["Jahr"] = df["Datum"].dt.year

        # Leere Liste für KPI-Infos
        kpi_rows = []

        for depot in depots_unique:
            df_depot = df[df["Depot"] == depot].sort_values(by="Datum")

            einzahlungen_total = df_depot["Einzahlungen Total (CHF)"].sum()
            letzter_kontostand = df_depot["Kontostand Total (CHF)"].iloc[-1]
            erstes_datum = df_depot["Datum"].iloc[0]
            letztes_datum = df_depot["Datum"].iloc[-1]
            jahre = (letztes_datum - erstes_datum).days / 365.25

            rendite_total = (
                (letzter_kontostand - einzahlungen_total) / einzahlungen_total
                if einzahlungen_total > 0
                else np.nan
            )
            rendite_p_a = (
                (1 + rendite_total) ** (1 / jahre) - 1 if (jahre > 0 and not np.isnan(rendite_total)) else np.nan
            )

            # YTD Rendite berechnen (letzter Kontostand dieses Jahr - Einzahlungen dieses Jahr) / Einzahlungen dieses Jahr
            aktuelles_jahr = letztes_datum.year
            df_ytd = df_depot[df_depot["Datum"].dt.year == aktuelles_jahr]
            einzahlungen_ytd = df_ytd["Einzahlungen Total (CHF)"].sum()
            kontostand_ytd = df_ytd["Kontostand Total (CHF)"].iloc[-1] if not df_ytd.empty else np.nan
            rendite_ytd = (
                (kontostand_ytd - einzahlungen_ytd) / einzahlungen_ytd
                if einzahlungen_ytd > 0
                else np.nan
            )

            # Akkumulierte Einzahlungen pro Jahr
            df_yearly = (
                df_depot.groupby("Jahr")["Einzahlungen Total (CHF)"]
                .sum()
                .reset_index()
                .rename(columns={"Einzahlungen Total (CHF)": "Akk. Einzahlungen CHF"})
            )

            # Zeilen für Tabelle pro Jahr mit KPIs erstellen
            for _, row_year in df_yearly.iterrows():
                jahr = int(row_year["Jahr"])
                einzahlungen_jahr = row_year["Akk. Einzahlungen CHF"]

                # Kontostand letztes Datum dieses Jahres
                df_jahr = df_depot[df_depot["Jahr"] == jahr]
                kontostand_jahr = df_jahr["Kontostand Total (CHF)"].iloc[-1]

                rendite_jahr = (
                    (kontostand_jahr - einzahlungen_jahr) / einzahlungen_jahr
                    if einzahlungen_jahr > 0
                    else np.nan
                )

                kpi_rows.append(
                    {
                        "Depot": depot,
                        "Jahr": jahr,
                        "Akk. Einzahlungen (CHF)": einzahlungen_jahr,
                        "Kontostand (CHF)": kontostand_jahr,
                        "Rendite Jahr (%)": rendite_jahr * 100 if not np.isnan(rendite_jahr) else None,
                    }
                )

            # Gesamt-KPI-Zeile
            kpi_rows.append(
                {
                    "Depot": depot,
                    "Jahr": "Gesamt",
                    "Akk. Einzahlungen (CHF)": einzahlungen_total,
                    "Kontostand (CHF)": letzter_kontostand,
                    "Rendite Jahr (%)": rendite_total * 100 if not np.isnan(rendite_total) else None,
                }
            )

        # KPI DataFrame
        kpi_df = pd.DataFrame(kpi_rows)

        # Tabelle anzeigen
        st.dataframe(kpi_df.style.format({"Akk. Einzahlungen (CHF)": "{:,.2f}",
                                          "Kontostand (CHF)": "{:,.2f}",
                                          "Rendite Jahr (%)": "{:.2f}"}))

    else:
        st.info("Noch keine Einträge vorhanden.")
