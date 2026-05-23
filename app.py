import streamlit as st
import pandas as pd
import re
from io import BytesIO
from PIL import Image
import easyocr
import numpy as np
import unicodedata
st.set_page_config(page_title="Analyseur Hippique", layout="wide")

@st.cache_resource
def get_reader():
    return easyocr.Reader(['en'], gpu=False)
def normalize_name(name):
    if not name:
        return ""

    name = str(name).upper()

    name = unicodedata.normalize("NFD", name)
    name = "".join(
        c for c in name
        if unicodedata.category(c) != "Mn"
    )

    name = re.sub(r"[^A-Z0-9]", "", name)

    return name
def extract_percentages(text):
    pattern = r"(.+?)\s*\((\d+[\.,]\d+)%\)"
    matches = re.findall(pattern, text)
    data = {}

    for name, pct in matches:
        clean = re.sub(r"\s+", " ", name).strip()
        if clean:
            data[clean.lower()] = (clean, float(pct.replace(',', '.')))

    return data
def extract_names(text):
    horses = []

    for line in text.splitlines():
        clean = line.strip()

        if not clean:
            continue

        match = re.match(r"^\s*(\d+)\s+(.+?)\s*$", clean)

        if match:
            number = str(match.group(1)).strip()
            name = str(match.group(2)).strip()

            horses.append({
                "numero": number,
                "nom": name,
                "key": normalize_name(name)
            })
        else:
            horses.append({
                "numero": "",
                "nom": clean,
                "key": normalize_name(clean)
            })

    return horses

def image_to_text(images):
    reader = get_reader()
    combined = []

    for img in images:
        image = Image.open(img).convert("RGB")
        arr = np.array(image)

        results = reader.readtext(arr, detail=1)

        items = []

        for item in results:
            bbox = item[0]
            text = str(item[1]).strip()

            if not text:
                continue

            x = min(p[0] for p in bbox)
            y = min(p[1] for p in bbox)

            items.append({
                "x": x,
                "y": y,
                "text": text
            })

        # Trier verticalement
        items.sort(key=lambda z: z["y"])

        grouped = []
        current_row = []

        for item in items:
            if not current_row:
                current_row.append(item)
            else:
                if abs(item["y"] - current_row[-1]["y"]) < 25:
                    current_row.append(item)
                else:
                    grouped.append(current_row)
                    current_row = [item]

        if current_row:
            grouped.append(current_row)

        lines = []

        for row in grouped:
            row.sort(key=lambda z: z["x"])

            if len(row) >= 2:
                number = row[0]["text"]
                name = " ".join(cell["text"] for cell in row[1:])

                if number.isdigit():
                    lines.append(f"{number} {name}")
                else:
                    lines.append(name)

            elif len(row) == 1:
                lines.append(row[0]["text"])

        combined.extend(lines)

    return "\n".join(combined)
def dataframe_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Classement")
    return output.getvalue()

page = st.sidebar.radio(
    "Choisir une page",
    ["Course ciblée", "Base complète Boturfers"]
)

# PAGE 1
if page == "Course ciblée":
    st.title("Analyse d'une course ciblée")
    st.write("Classe uniquement les chevaux de votre course.")

    bot_text = st.text_area(
        "Base Boturfers (texte avec pourcentages)",
        height=250
    )

    bot_images = st.file_uploader(
        "Ou téléversez des captures Boturfers",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    race_text = st.text_area(
        "Liste des chevaux de votre course (un cheval par ligne)",
        height=200
    )

    race_images = st.file_uploader(
        "Ou téléversez des captures de la liste de votre course",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    if st.button("Filtrer et classer"):
        if bot_images:
            bot_text += "\n" + image_to_text(bot_images)

        if race_images:
            race_text += "\n" + image_to_text(race_images)

        if not bot_text.strip():
            st.warning("Veuillez fournir la base Boturfers.")
        elif not race_text.strip():
            st.warning("Veuillez fournir la liste de votre course.")
        else:
            percentages = extract_percentages(bot_text)
            race_names = extract_names(race_text)
            results = []
            seen = set()

            normalized_percentages = {}

            for key, value in percentages.items():
                normalized_key = normalize_name(key)
                normalized_percentages[normalized_key] = value

            for horse in race_names:
                key = horse["key"]

                if key in normalized_percentages and key not in seen:
                    seen.add(key)

                    display, pct = normalized_percentages[key]

                    results.append(
                        (
                            horse["numero"],
                            display,
                            pct
                        )
                    )

            if results:
                results.sort(key=lambda x: x[2], reverse=True)

                df = pd.DataFrame(
                    results,
                    columns=["N°", "Cheval", "Pourcentage"]
                )

                

                st.success(f"{len(df)} chevaux trouvés")
                st.dataframe(df, use_container_width=True, hide_index=True)

                excel = dataframe_to_excel(df)

                st.download_button(
                    "Télécharger Excel",
                    excel,
                    "classement_course.xlsx"
                )
            else:
                st.warning("Aucun cheval correspondant trouvé.")

# PAGE 2
else:
    st.title("Base complète Boturfers")
    st.write("Classement global de toute votre base.")

    base_text = st.text_area(
        "Collez la base complète",
        height=300
    )

    base_images = st.file_uploader(
        "Ou téléversez des captures",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    top_choice = st.selectbox(
        "Afficher",
        ["Tout", "Top 5", "Top 10", "Top 20"]
    )

    search = st.text_input("Rechercher un cheval")

    if st.button("Analyser la base"):
        if base_images:
            base_text += "\n" + image_to_text(base_images)

        if not base_text.strip():
            st.warning("Veuillez fournir des données.")
        else:
            percentages = extract_percentages(base_text)

            rows = [
                (name, pct)
                for _, (name, pct) in percentages.items()
            ]

            rows.sort(key=lambda x: x[1], reverse=True)

            df = pd.DataFrame(
                rows,
                columns=["Cheval", "Pourcentage"]
            )

            if search:
                df = df[
                    df["Cheval"].str.contains(
                        search,
                        case=False,
                        na=False
                    )
                ]

            if top_choice == "Top 5":
                df = df.head(5)
            elif top_choice == "Top 10":
                df = df.head(10)
            elif top_choice == "Top 20":
                df = df.head(20)

            

            st.success(f"{len(df)} chevaux analysés")
            st.dataframe(df, use_container_width=True, hide_index=True)

            excel = dataframe_to_excel(df)

            st.download_button(
                "Télécharger Excel",
                excel,
                "base_complete.xlsx"
            )
