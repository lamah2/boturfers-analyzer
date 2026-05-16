import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Analyseur de course", layout="wide")

st.title("Analyseur de course hippique")
st.write("Collez la base Boturfers + les chevaux de votre course.")

def extract_percentages(text):
    pattern = r"(.+?)\s*\((\d+,\d+)%\)"
    matches = re.findall(pattern, text)

    data = {}

    for name, pct in matches:
        clean_name = name.strip().lower()
        percentage = float(pct.replace(",", "."))
        data[clean_name] = percentage

    return data


def extract_race_horses(text):
    horses = []
    lines = text.splitlines()

    for line in lines:
        clean = line.strip()
        if clean:
            horses.append(clean)

    return horses


def to_excel(df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Classement")

    return output.getvalue()


boturfers_text = st.text_area(
    "Base complète Boturfers",
    height=300,
    placeholder="Collez ici toute la liste Boturfers..."
)

race_text = st.text_area(
    "Chevaux de votre course",
    height=200,
    placeholder="""Exemple :
Dedel
Hamavi
Dream Weaver
Agiota"""
)

if st.button("Filtrer et classer"):
    if boturfers_text and race_text:
        percentages = extract_percentages(boturfers_text)
        race_horses = extract_race_horses(race_text)

        results = []

        for horse in race_horses:
            key = horse.lower()
            if key in percentages:
                results.append((horse, percentages[key]))

        if results:
            results.sort(key=lambda x: x[1], reverse=True)

            df = pd.DataFrame(results, columns=["Cheval", "Pourcentage"])
            df.insert(0, "Rang", range(1, len(df) + 1))

            st.success(f"{len(results)} chevaux trouvés dans votre course")
            st.dataframe(df, use_container_width=True)

            excel_file = to_excel(df)

            st.download_button(
                "Télécharger Excel",
                excel_file,
                "classement_course.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Aucun cheval correspondant trouvé.")
