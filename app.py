import streamlit as st
import pandas as pd
from datetime import datetime

st.title("Depot Tracker - Quartalsweise Eingaben")

# Beispiel-Depots
depots = ["3a Yvan – VZ","3a Yvan – Finpension", "3a Vanessa - Frankly", "ETF Yvan – VZ", "ETF Yvan - True Wealth]

# Eingabeformular
with st.form(key="depot_form"):
    depot = st.selectbox("Depot auswählen", depots)
    datum = st.date_input("Datum auswählen")
    einzahlungen = st.number_input("Einzahlungen Total (CHF)", min_value=0.0, format="%.2f")
    kontostand = st.number_input("Kontostand Total (CHF)", min_value=0.0, format="%.2f")

    submit = st.form_submit_button("Daten speichern")

# Daten speichern im Session State
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Depot", "Datum", "Einzahlungen Total", "Kontostand Total"])

if submit:
    neue_zeile = {
        "Depot": depot,
        "Datum": datum.strftime("%d-%m-%Y"),  # TT-MM-JJJJ
        "Einzahlungen Total": einzahlungen,
        "Kontostand Total": kontostand,
    }
    st.session_state.data = st.session_state.data.append(neue_zeile, ignore_index=True)
    st.success("Daten gespeichert!")

# Tabelle anzeigen
if not st.session_state.data.empty:
    st.write("Bisherige Einträge:")
    st.dataframe(st.session_state.data)
else:
    st.write("Noch keine Daten eingetragen.")
