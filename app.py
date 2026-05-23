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

        h, w = arr.shape[:2]

        # OCR avec coordonnées
        results = reader.readtext(arr, detail=1)

        rows = []

        for item in results:
            bbox = item[0]
            text = str(item[1]).strip()

            if not text:
                continue

            x = min(p[0] for p in bbox)
            y = min(p[1] for p in bbox)

            if text.upper() in ["N°", "CHEVAUX"]:
                continue

            rows.append({
                "x": x,
                "y": y,
                "text": text
            })

        # tri vertical
        rows.sort(key=lambda r: r["y"])

        grouped = []

        for item in rows:
            matched = False

            for group in grouped:
                if abs(group["y"] - item["y"]) < 20:
                    group["items"].append(item)
                    matched = True
                    break

            if not matched:
                grouped.append({
                    "y": item["y"],
                    "items": [item]
                })

        lines = []

        for group in grouped:
            group["items"].sort(key=lambda z: z["x"])

            number = ""
            name_parts = []

            for cell in group["items"]:
                txt = cell["text"]

                if txt.isdigit() and cell["x"] < w * 0.25:
                    number = txt
                else:
                    name_parts.append(txt)

            if name_parts:
                horse_name = " ".join(name_parts)

                if number:
                    lines.append(f"{number} {horse_name}")
                else:
                    lines.append(horse_name)

        combined.extend(lines)

    return "\n".join(combined)
def dataframe_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Classement")
    return output.getvalue()

page = st.sidebar.radio(
    "Choisir une page",
    [
        "Course ciblée",
        "Base complète Boturfers",
        "Pronostics experts"
    ]
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
# PAGE 3
elif page == "Pronostics experts":
    st.title("Pronostics experts pondérés")

    pct_text = st.text_area(
        "Classement pourcentage",
        height=80,
        placeholder="9 15 1 4 6 2 10 11"
    )

    zeturf_text = st.text_area(
        "Pronostic ZEturf",
        height=80,
        placeholder="9 1 4 6 2 7 3"
    )

    geny_text = st.text_area(
        "Pronostic Genybet",
        height=80,
        placeholder="1 9 6 3 4 8 2 11"
    )

    turf_text = st.text_area(
        "Pronostic Turfomania",
        height=80,
        placeholder="1 6 9 5 2 4 12 7"
    )
    def parse_pronostic(text):
        nums = re.findall(r"\d+", text)
        return nums

    def weighted_scores(nums, source_name):
        scores = {}
        total = len(nums)

        for i, num in enumerate(nums):
            points = total - i
            scores[num] = {
                "points": points,
                "source": source_name
            }

        return scores

    if st.button("Calculer consensus"):
        all_scores = {}
        all_sources = {}

        sources_data = [
            (pct_text, "Pourcentage"),
            (zeturf_text, "ZEturf"),
            (geny_text, "Genybet"),
            (turf_text, "Turfomania")
        ]

        for txt, src in sources_data:
            nums = parse_pronostic(txt)
            scored = weighted_scores(nums, src)

            for num, info in scored.items():
                if num not in all_scores:
                    all_scores[num] = 0
                    all_sources[num] = []

                all_scores[num] += info["points"]
                all_sources[num].append(src)

        if all_scores:
            rows = []

            for num in all_scores:
                rows.append({
                    "N°": num,
                    "Score total": all_scores[num],
                    "Sources": ", ".join(all_sources[num])
                })

            df = pd.DataFrame(rows)
            df = df.sort_values("Score total", ascending=False)

            st.success("Consensus calculé")
            st.dataframe(df, use_container_width=True, hide_index=True)
