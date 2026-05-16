import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Analyseur chevaux", layout="wide")

st.title("Analyseur de chevaux")
st.write("Collez ici la liste des chevaux avec leurs pourcentages.")

def extract_data(text):
    pattern = r"(.+?)\s*\((\d+,\d+)%\)"
    matches = re.findall(pattern, text)

    results = []

    for name, pct in matches:
        clean_name = name.strip()
        percentage = float(pct.replace(",", "."))
        results.append((clean_name, percentage))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def to_excel(data):
    df = pd.DataFrame(data, columns=["Cheval", "Pourcentage"])
    df.insert(0, "Rang", range(1, len(df) + 1))

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Classement")

    return output.getvalue()


horse_text = st.text_area(
    "Collez votre liste ici",
    height=400,
    placeholder="""Exemple :
Afyon (6,81%)
Agiota (17,85%)
Alhunter (4,49%)
Alicanto (10,54%)"""
)

if st.button("Classer les chevaux"):
    if horse_text.strip():
        data = extract_data(horse_text)

        if data:
            st.success(f"{len(data)} chevaux analysés")

            df = pd.DataFrame(data, columns=["Cheval", "Pourcentage"])
            df.index = df.index + 1

            st.dataframe(df, use_container_width=True)

            excel_file = to_excel(data)

            st.download_button(
                label="Télécharger Excel",
                data=excel_file,
                file_name="classement_chevaux.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Aucune donnée reconnue. Vérifiez le format.")
