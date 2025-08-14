import json
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from string import punctuation
from nltk.corpus import stopwords

# === Configuration ===
data_dir = "C:/Users/pc/Desktop/NewData/data/natures_new"
lemmes_dir = "C:/Users/pc/Desktop/NewData/data/resultats_par_nature"
output_dir = "C:/Users/pc/Desktop/NewData/data/prediction/prediction_results/new_data"
os.makedirs(output_dir, exist_ok=True)

# === Stopwords ===
STOPWORDS = set(stopwords.words("french"))

# === Nettoyage et normalisation du texte ===
def clean_and_tokenize(text):
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(rf"[{punctuation}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    tokens = [t for t in text.strip().split() if t not in STOPWORDS and len(t) > 2]
    return set(tokens)

# === Parse montant ===
def parse_montant(montant_str):
    montant_str = montant_str.replace("MAD", "").replace(",", ".").replace(" ", "")
    try:
        return float(montant_str)
    except:
        return None

# === Fonction pour nom fichier nature ===
def normaliser_nom_fichier_nature(nature):
    nom = nature.replace(' ', '_').replace('/', '_')
    return nom

# === Prédiction ===
for filename in os.listdir(data_dir):
    if not filename.endswith(".jsonl"):
        continue

    filepath = os.path.join(data_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]

    detailed_results = []
    stats_by_nature = defaultdict(lambda: {"total": 0, "correct": 0})

    for item in entries:
        nature = item.get("nature")
        text = item.get("text", "")
        montant_real = parse_montant(item.get("montant", ""))
        reference = item.get("reference", "")

        if not nature:
            continue

        nature_filename = f"{normaliser_nom_fichier_nature(nature)}.json"
        lemme_file = os.path.join(lemmes_dir, nature_filename)

        if not os.path.exists(lemme_file):
            print(f"⚠️  Fichier introuvable pour nature: {nature} → {lemme_file}")
            continue

        racines = clean_and_tokenize(text)

        with open(lemme_file, "r", encoding="utf-8") as f:
            interv_dict = json.load(f)

        best_match = None
        max_overlap = 0

        for interval_str, ref_racines in interv_dict.items():
            intersection = len(set(ref_racines) & racines)
            if intersection > max_overlap:
                best_match = interval_str
                max_overlap = intersection

        if best_match:
            predicted_min, predicted_max = map(float, best_match.split("-"))
            correct = predicted_min <= montant_real < predicted_max if montant_real is not None else False
        else:
            predicted_min = predicted_max = None
            correct = False

        stats_by_nature[nature]["total"] += 1
        if correct:
            stats_by_nature[nature]["correct"] += 1

        detailed_results.append({
            "reference": reference,
            "nature": nature,
            "real_montant": montant_real,
            "predicted_interval": best_match,
            "correct": correct,
            "text": text,
            "tokens": sorted(list(racines))
        })

    # Sauvegarde des résultats
    date_part = filename.replace("merged_output_strict_montant_", "").replace(".jsonl", "")
    result_path = os.path.join(output_dir, f"results_{date_part}.json")
    stats_path = os.path.join(output_dir, f"stats_{date_part}.json")

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(detailed_results, f, ensure_ascii=False, indent=2)

    with open(stats_path, "w", encoding="utf-8") as f:
        stats_pct = {
            nature: {
                **vals,
                "accuracy": round(vals["correct"] / vals["total"] * 100, 2) if vals["total"] else 0
            }
            for nature, vals in stats_by_nature.items()
        }
        json.dump(stats_pct, f, ensure_ascii=False, indent=2)

    print(f"✅ {filename} → {len(detailed_results)} éléments prédits, stats enregistrées.")
