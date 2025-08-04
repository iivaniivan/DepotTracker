import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime

# Zugangsschutz (empfohlen via secrets.toml)
def check_login():
    st.sidebar.title("🔒 Login erforderlich")
    username_input = st.sidebar.text_input("Benutzername")
    password_input = st.sidebar.text_input("Passwort", type="password")

    if username_input == "yvan" and password_input == "Depot2025":
        return True
    else:
        st.sidebar.warning("Bitte gültige Login-Daten eingeben.")
        st.stop()

check_login()

st.title("Depot-Tracker 📈")

tab1, tab2 = st.tabs(["Neue Werte eingeben", "Depotentwicklung & Kennzahlen"])

with tab1:
    st.header("Neue Werte erfassen")
    uploaded_file = st.file_uploader("📤 CSV-Datei hochladen", type=["csv"])
    if uploaded_file:
        df_new = pd.read_csv(uploaded_file)
        st.success("Datei erfolgreich geladen:")
        st.write(df_new)

with tab2:
    st.header("📊 Depotentwicklung & Kennzahlen")

    uploaded_file = st.file_uploader("📤 CSV für Auswertung", type=["csv"], key="file2")
    if uploaded_file:
        df = pd.read_csv(uploaded_file, parse_dates=["Datum"])
        df["Datum"] = pd.to_datetime(df["Datum"])
        df = df.sort_values("Datum")

        # Chart
        st.subheader("📈 Entwicklung der Depots")
        fig, ax = plt.subplots(figsize=(12, 4))
        depots = df["Depot"].unique()
        farben = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

        for i, depot in enumerate(depots):
            df_depot = df[df["Depot"] == depot]
            ax.plot(df_depot["Datum"], df_depot["Kontostand Total (CHF)"], label=depot, color=farben[i % len(farben)])

        ax.set_title("Entwicklung der Depotwerte über die Zeit")
        ax.set_xlabel("Datum")
        ax.set_ylabel("Kontostand (CHF)")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

        # KPIs
        st.subheader("🔢 Kennzahlen pro Depot")

        for depot in df["Depot"].unique():
            df_depot = df[df["Depot"] == depot].sort_values("Datum")

            df_depot["Einzahlung pro Zeile"] = df_depot["Einzahlungen Total (CHF)"].diff().fillna(df_depot["Einzahlungen Total (CHF)"])

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

            tage = (df_depot["Datum"].iloc[-1] - df_depot["Datum"].iloc[0]).days
            jahre = tage / 365.25 if tage > 0 else 1
            rendite_p_a = (1 + rendite_total) ** (1 / jahre) - 1 if jahre > 0 else 0

            letzter_kontostand = df_depot["Kontostand Total (CHF)"].iloc[-1]
            einzahlungen_total = df_depot["Einzahlungen Total (CHF)"].iloc[-1]
            rendite_einfach = (letzter_kontostand - einzahlungen_total) / einzahlungen_total if einzahlungen_total > 0 else 0

            st.markdown(f"### 📌 {depot}")
            col1, col2, col3, col4, col5 = st.columns([2.5, 2.5, 1.5, 1.5, 1.5])
            col1.metric("Einzahlungen", f"CHF {einzahlungen_total:,.0f}")
            col2.metric("Letzter Stand", f"CHF {letzter_kontostand:,.0f}")
            col3.metric("Einfache Rendite", f"{rendite_einfach*100:.2f}%")
            col4.metric("Rendite total (TWR)", f"{rendite_total*100:.2f}%")
            col5.metric("Rendite p.a. (TWR)", f"{rendite_p_a*100:.2f}%")
