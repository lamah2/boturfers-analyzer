import streamlit as st
import pandas as pd
import time
import re
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


st.set_page_config(page_title="Analyseur Boturfers", layout="wide")
st.title("Analyseur Boturfers")
st.write("Collez un lien Boturfers (quinte-du-jour ou page course).")


def extract_data(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(url)
        time.sleep(5)

        text = driver.page_source
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

    finally:
        driver.quit()


def to_excel(data):
    df = pd.DataFrame(data, columns=["Cheval", "Pourcentage"])
    df.insert(0, "Rang", range(1, len(df) + 1))

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Classement")
    return output.getvalue()


url = st.text_input("Lien Boturfers")

if st.button("Analyser"):
    if url:
        with st.spinner("Analyse en cours..."):
            data = extract_data(url)

        if data:
            st.success(f"{len(data)} chevaux trouvés")
            df = pd.DataFrame(data, columns=["Cheval", "Pourcentage"])
            df.index = df.index + 1
            st.dataframe(df)

            excel_file = to_excel(data)
            st.download_button(
                "Télécharger Excel",
                excel_file,
                "classement_boturfers.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Aucune donnée trouvée.")
