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
    st.header("Entwicklung & Kennzahlen")

    # Daten aus Google Sheet laden
    rows = sheet.get_all_records()
    df = pd.DataFrame(rows)

    # Falls Spalten als Zahl formatiert sind, sind sie schon float, sonst ggf. casten
    # Wenn Spalten schon numerisch sind, brauchst du keine Umwandlung
    # Nur falls du Strings hast, dann so:
    try:
        df["Einzahlungen Total (CHF)"] = pd.to_numeric(df["Einzahlungen Total (CHF)"])
        df["Kontostand Total (CHF)"] = pd.to_numeric(df["Kontostand Total (CHF)"])
    except Exception:
        pass

    # Datum parsen
    df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%Y")

    # Quartal extrahieren
    df["Jahr"] = df["Datum"].dt.year
    df["Quartal"] = df["Datum"].dt.to_period("Q")
    df["Quartal_kurz"] = df["Quartal"].apply(lambda x: f"Q{x.quarter}/{str(x.year)[2:]}")

    # Sortierte Quartale (optional)
    quartale_sort = sorted(df["Quartal_kurz"].unique(), key=lambda x: (int(x.split("/")[1]), int(x[1])))

        st.subheader("📊 Kompakte Kennzahlenübersicht")

    for depot in df["Depot"].unique():
        df_depot = df[df["Depot"] == depot].sort_values("Datum")
        letzter_kontostand = df_depot["Kontostand Total (CHF)"].iloc[-1]
        einzahlungen_total = df_depot["Einzahlungen Total (CHF)"].iloc[-1]

        if einzahlungen_total > 0:
            rendite_total = (letzter_kontostand - einzahlungen_total) / einzahlungen_total
        else:
            rendite_total = 0.0

        tage = (df_depot["Datum"].iloc[-1] - df_depot["Datum"].iloc[0]).days
        jahre = tage / 365 if tage > 0 else 0
        rendite_p_a = ((letzter_kontostand / einzahlungen_total) ** (1 / jahre)) - 1 if jahre > 0 and einzahlungen_total > 0 else 0.0

        with st.expander(f"📈 {depot}"):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Einzahlungen", f"CHF {einzahlungen_total:,.0f}")
            col2.metric("Letzter Stand", f"CHF {letzter_kontostand:,.0f}")
            col3.metric("Rendite total", f"{rendite_total*100:.2f}%")
            col4.metric("Rendite p.a.", f"{rendite_p_a*100:.2f}%")

            # 🧮 Jahresrenditen
            df_depot['Jahr'] = df_depot['Datum'].dt.year
            jahres_renditen = []
            for jahr in sorted(df_depot['Jahr'].unique()):
                df_jahr = df_depot[df_depot['Jahr'] == jahr]
                startwert = df_jahr["Kontostand Total (CHF)"].iloc[0]
                endwert = df_jahr["Kontostand Total (CHF)"].iloc[-1]
                if startwert > 0:
                    rendite = (endwert - startwert) / startwert
                else:
                    rendite = 0.0
                jahres_renditen.append({"Jahr": jahr, "Rendite p.a.": f"{rendite*100:.2f}%"})

            st.markdown("**📅 Jahresrenditen:**")
            st.table(pd.DataFrame(jahres_renditen))

    #import pandas as pd
import plotly.express as px

# Datum konvertieren und sortieren
df['Datum'] = pd.to_datetime(df['Datum'], format="%d.%m.%Y", errors='coerce')
df = df.sort_values(by='Datum')

# Optional: Quartals-Spalte erzeugen, falls gewünscht
df['Quartal'] = df['Datum'].dt.to_period('Q').astype(str)

# Chart erstellen
fig = px.line(
    df,
    x="Datum",            # exaktes Datum (nicht nur Quartal)
    y="Kontostand Total (CHF)",        # <-- anpassen, falls deine Spalte anders heißt
    color="Depot",    # <-- anpassen, falls du mehrere Depots vergleichst
    markers=True,
)

# X-Achse formatieren: Quartale als Tick-Labels
fig.update_layout(
    xaxis=dict(
        tickformat="%Y-Q%q",  # z. B. 2024-Q2
        title="Datum"
    ),
    yaxis_title="Depotwert",
    title="Depotentwicklung über Zeit",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

