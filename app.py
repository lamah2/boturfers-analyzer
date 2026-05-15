import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Boturfers Analyzer", layout="wide")
st.title("Analyseur Boturfers")
st.write("Collez un lien Boturfers (quinte-du-jour ou page course).")

def extract_data(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(" ")

    pattern = r"([A-Za-zÀ-ÿ' -]+)\s*\((\d+,\d+)%\)"
    matches = re.findall(pattern, text)

    results = []
    seen = set()

    for name, pct in matches:
        clean_name = re.sub(r"\s+", " ", name).strip()

        if clean_name and clean_name not in seen:
            seen.add(clean_name)
            results.append((clean_name, float(pct.replace(",", "."))))

    results.sort(key=lambda x: x[1], reverse=True)
    return results

def to_excel(data):
    df = pd.DataFrame(data, columns=["Cheval", "Pourcentage"])
    df.insert(0, "Rang", range(1, len(df)+1))

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Classement")

    output.seek(0)
    return output

url = st.text_input("Lien Boturfers")

if st.button("Analyser"):
    if not url:
        st.error("Veuillez coller un lien Boturfers.")
    else:
        try:
            data = extract_data(url)

            if not data:
                st.warning("Aucune donnée trouvée.")
            else:
                df = pd.DataFrame(data, columns=["Cheval", "Pourcentage"])
                df.insert(0, "Rang", range(1, len(df)+1))

                st.dataframe(df, use_container_width=True)

                excel_file = to_excel(data)

                st.download_button(
                    label="Télécharger Excel",
                    data=excel_file,
                    file_name="classement_boturfers.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"Erreur : {e}")