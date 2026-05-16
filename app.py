import streamlit as st
import requests
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="Analyseur Boturfers", layout="wide")
st.title("Analyseur Boturfers")
st.write("Collez un lien Boturfers (quinte-du-jour ou page course).")


def extract_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(url, headers=headers, timeout=20)
    html = r.text

    results = []

    pattern = r'"name":"([^"]+)".*?"percentage":"([\d,]+)"'
    matches = re.findall(pattern, html)

    seen = set()

    for name, pct in matches:
        clean_name = name.strip()
        if clean_name not in seen:
            seen.add(clean_name)
            results.append((clean_name, float(pct.replace(",", "."))))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def to_excel(data):
    df = pd.DataFrame(data, columns=["Cheval", "Pourcentage"])
    df.insert(0, "Rang", range(1, len(df) + 1))

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    return output.getvalue()


url = st.text_input("Lien Boturfers")

if st.button("Analyser"):
    if url:
        try:
            data = extract_data(url)

            if data:
                st.success(f"{len(data)} chevaux trouvés")

                df = pd.DataFrame(data, columns=["Cheval", "Pourcentage"])
                df.index += 1
                st.dataframe(df)

                excel = to_excel(data)

                st.download_button(
                    "Télécharger Excel",
                    excel,
                    "classement.xlsx"
                )

            else:
                st.warning("Aucune donnée trouvée.")

        except Exception as e:
            st.error(str(e))
