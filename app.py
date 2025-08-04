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
    import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Depottracker")

# Daten laden (Beispielhaft als CSV, anpassen bei Google Sheets oder Datenbank)
df = pd.read_csv("depotdaten.csv")

# Bereinigung der Beträge (CHF-Strings zu floats)
def parse_chf(value):
    if isinstance(value, str):
        value = value.replace("CHF", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(value)
    except:
        return np.nan

df["Einzahlungen Total (CHF)"] = df["Einzahlungen Total (CHF)"].apply(parse_chf)
df["Kontostand Total (CHF)"] = df["Kontostand Total (CHF)"].apply(parse_chf)

# Datum formatieren
df["Datum"] = pd.to_datetime(df["Datum"], dayfirst=True)
df = df.dropna(subset=["Einzahlungen Total (CHF)", "Kontostand Total (CHF)"])

# Dropdown-Auswahl für Chart
alle_depots = df["Depot"].unique().tolist()
auswahl_depots = st.multiselect("Depot auswählen für Chart", options=alle_depots, default=alle_depots)
df_chart = df[df["Depot"].isin(auswahl_depots)]

# Chart vorbereiten
if not df_chart.empty:
    chart = alt.Chart(df_chart).mark_line(point=True).encode(
        x=alt.X("Datum:T", title="Datum", axis=alt.Axis(format="%b %y")),
        y=alt.Y("Kontostand Total (CHF):Q", title="Kontostand", scale=alt.Scale(zero=False)),
        color="Depot"
    ).properties(
        title="Entwicklung pro Depot",
        width=900,
        height=400
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("Keine Daten für ausgewählte Depots.")

# Quartalsspalte erzeugen für Gruppierung
df["Jahr"] = df["Datum"].dt.year
df["Quartal"] = df["Datum"].dt.to_period("Q")
df["Quartal_kurz"] = df["Quartal"].astype(str).str.replace("Q", "Q").str[5:] + "/" + df["Jahr"].astype(str).str[2:]

# Sortierung der Quartale
try:
    quartale_sort = sorted(df["Quartal_kurz"].unique(), key=lambda x: (
        int(x[1]),  # Q1 = 1, Q2 = 2 etc.
        int("20" + x[3:])  # Jahr 25 → 2025
    ))
except:
    quartale_sort = df["Quartal_kurz"].unique().tolist()

# KPIs pro Depot und Jahr
st.subheader("KPIs pro Depot und Jahr")

kpi_data = []

for depot in alle_depots:
    df_depot = df[df["Depot"] == depot].copy()
    if df_depot.empty:
        continue

    letzter_kontostand = df_depot.sort_values("Datum")["Kontostand Total (CHF)"].iloc[-1]
    einzahlungen_total = df_depot["Einzahlungen Total (CHF)"].max()

    try:
        rendite_total = (letzter_kontostand - einzahlungen_total) / einzahlungen_total
    except Exception as e:
        rendite_total = np.nan

    # YTD-Berechnung
    aktuelles_jahr = datetime.today().year
    df_ytd = df_depot[df_depot["Datum"].dt.year == aktuelles_jahr]
    if not df_ytd.empty:
        ytd_start = df_ytd.sort_values("Datum")["Kontostand Total (CHF)"].iloc[0]
        ytd_ende = df_ytd.sort_values("Datum")["Kontostand Total (CHF)"].iloc[-1]
        rendite_ytd = (ytd_ende - ytd_start) / ytd_start
    else:
        rendite_ytd = np.nan

    # Einzahlungen pro Jahr
    einzahlungen_pro_jahr = df_depot.groupby("Jahr")["Einzahlungen Total (CHF)"].max().diff().fillna(df_depot.groupby("Jahr")["Einzahlungen Total (CHF)"].max())

    for jahr, einzahlung in einzahlungen_pro_jahr.items():
        kpi_data.append({
            "Depot": depot,
            "Jahr": int(jahr),
            "Einzahlungen": round(einzahlung, 2),
            "Rendite YTD": round(rendite_ytd * 100, 2) if not np.isnan(rendite_ytd) else None,
            "Rendite Total": round(rendite_total * 100, 2) if not np.isnan(rendite_total) else None,
            "Kontostand aktuell": round(letzter_kontostand, 2)
        })

if kpi_data:
    df_kpi = pd.DataFrame(kpi_data)
    st.dataframe(df_kpi)
else:
    st.info("Keine KPIs verfügbar.")

