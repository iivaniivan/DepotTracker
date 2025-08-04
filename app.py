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

    try:
        records = sheet.get_all_records()
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        records = []

    if records:
        df = pd.DataFrame(records)
        df = df.sort_values(by="Datum", ascending=True)

        # Datum in datetime konvertieren
        df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%Y", errors='coerce')

        if df["Datum"].isnull().any():
            st.warning("Es gibt ungültige Datumsangaben, diese werden ignoriert.")
            df = df.dropna(subset=["Datum"])

        # Quartalsspalte Q1/25 etc.
        df["Quartal"] = df["Datum"].dt.to_period("Q").astype(str)
        # Kürzeres Format z.B. "Q1/25"
        df["Quartal_kurz"] = df["Quartal"].apply(lambda x: "Q" + x[1] + "/" + x[2:4])

        depots_unique = df["Depot"].unique()
        selected_depots = st.multiselect(
            "Depot auswählen für Chart", depots_unique, default=depots_unique.tolist()
        )

        if selected_depots:
            df_chart = df[df["Depot"].isin(selected_depots)].copy()

            # Aggregiere Kontostand pro Quartal und Depot - max Wert pro Quartal
            df_q = (
                df_chart.groupby(["Quartal_kurz", "Depot"])["Kontostand Total (CHF)"]
                .max()
                .reset_index()
            )

            # Sortiere Quartale korrekt: Q1=1, Jahr 25=2025 etc.
            def quartal_sort_key(x):
                try:
                    quartal_num = int(x[1])       # "Q1/25" -> 1
                    jahr_num = int("20" + x[-2:]) # "Q1/25" -> 2025
                    return (jahr_num, quartal_num)
                except Exception:
                    return (9999, 99)  # Schlecht formatierte Werte ans Ende

            quartale_sort = sorted(df_q["Quartal_kurz"].unique(), key=quartal_sort_key)

            chart = (
                alt.Chart(df_q)
                .mark_line(point=True)
                .encode(
                    x=alt.X(
                        "Quartal_kurz:N",
                        sort=quartale_sort,
                        title="Quartal",
                    ),
                    y=alt.Y(
                        "Kontostand Total (CHF):Q",
                        title="Kontostand (CHF)",
                    ),
                    color="Depot:N",
                    tooltip=["Depot", "Quartal_kurz", "Kontostand Total (CHF)"],
                )
                .properties(width=700, height=400)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Bitte mindestens ein Depot auswählen.")

        st.markdown("---")
        st.header("KPIs pro Depot und Jahr")

        df["Jahr"] = df["Datum"].dt.year

        kpi_rows = []
        for depot in depots_unique:
            df_depot = df[df["Depot"] == depot].sort_values(by="Datum")

            if df_depot.empty:
                st.warning(f"Keine Daten für Depot '{depot}'.")
                continue

            einzahlungen_total = df_depot["Einzahlungen Total (CHF)"].sum()
            letzter_kontostand = df_depot["Kontostand Total (CHF)"].iloc[-1]
            erstes_datum = df_depot["Datum"].iloc[0]
            letztes_datum = df_depot["Datum"].iloc[-1]
            jahre = (letztes_datum - erstes_datum).days / 365.25

            # Rendite total berechnen mit Absicherung gegen Division durch 0
            if einzahlungen_total == 0 or pd.isna(einzahlungen_total):
                rendite_total = np.nan
            else:
                rendite_total = (letzter_kontostand - einzahlungen_total) / einzahlungen_total

            if jahre > 0 and not np.isnan(rendite_total):
                rendite_p_a = (1 + rendite_total) ** (1 / jahre) - 1
            else:
                rendite_p_a = np.nan

            aktuelles_jahr = letztes_datum.year
            df_ytd = df_depot[df_depot["Datum"].dt.year == aktuelles_jahr]

            einzahlungen_ytd = df_ytd["Einzahlungen Total (CHF)"].sum()
            kontostand_ytd = df_ytd["Kontostand Total (CHF)"].iloc[-1] if not df_ytd.empty else np.nan

            if einzahlungen_ytd == 0 or pd.isna(einzahlungen_ytd):
                rendite_ytd = np.nan
            else:
                rendite_ytd = (kontostand_ytd - einzahlungen_ytd) / einzahlungen_ytd

            df_yearly = (
                df_depot.groupby("Jahr")["Einzahlungen Total (CHF)"]
                .sum()
                .reset_index()
                .rename(columns={"Einzahlungen Total (CHF)": "Akk. Einzahlungen CHF"})
            )

            for _, row_year in df_yearly.iterrows():
                jahr = int(row_year["Jahr"])
                einzahlungen_jahr = row_year["Akk. Einzahlungen CHF"]
                df_jahr = df_depot[df_depot["Jahr"] == jahr]
                kontostand_jahr = df_jahr["Kontostand Total (CHF)"].iloc[-1]

                if einzahlungen_jahr == 0 or pd.isna(einzahlungen_jahr):
                    rendite_jahr = np.nan
                else:
                    rendite_jahr = (kontostand_jahr - einzahlungen_jahr) / einzahlungen_jahr

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

            # Zusätzlich Rendite p.a. als eigene Zeile
            kpi_rows.append(
                {
                    "Depot": depot,
                    "Jahr": "Rendite p.a.",
                    "Akk. Einzahlungen (CHF)": None,
                    "Kontostand (CHF)": None,
                    "Rendite Jahr (%)": rendite_p_a * 100 if not np.isnan(rendite_p_a) else None,
                }
            )

            # Rendite YTD hinzufügen
            kpi_rows.append(
                {
                    "Depot": depot,
                    "Jahr": f"Rendite YTD {aktuelles_jahr}",
                    "Akk. Einzahlungen (CHF)": None,
                    "Kontostand (CHF)": kontostand_ytd,
                    "Rendite Jahr (%)": rendite_ytd * 100 if not np.isnan(rendite_ytd) else None,
                }
            )

        if len(kpi_rows) == 0:
            st.warning("Keine KPIs berechnet, da keine Daten vorhanden sind.")
        else:
            kpi_df = pd.DataFrame(kpi_rows)

            st.dataframe(
                kpi_df.style.format(
                    {
                        "Akk. Einzahlungen (CHF)": "{:,.2f}",
                        "Kontostand (CHF)": "{:,.2f}",
                        "Rendite Jahr (%)": "{:.2f}",
                    }
                )
            )
    else:
        st.info("Noch keine Einträge vorhanden.")
