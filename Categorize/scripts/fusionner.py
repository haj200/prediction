import os
import json
import re

# --- Fonctions utilitaires ---
def clean(text):
    if not isinstance(text, str):
        return ""
    # Supprimer espaces, # et :
    text = re.sub(r"^[\s#:]+|[\s#:]+$", "", text)
    # Normaliser la casse (majuscules ou minuscules selon ce que tu préfères)
    return text.strip().upper()


def load_jsonl(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

# --- Fichiers sources ---
DAILY_DIR = "data_daily"
CONSULT_FILES = [
    "C:/Users/pc/Desktop/newNew/scraper/old_data/data/consultations.ndjson",
    "data_daily/consultations.ndjson"
]
DOUBLONS_FILE = "doublons.jsonl"
OUTPUT_DIR = "merged_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Chargement des doublons ---
doublons_data = load_jsonl(DOUBLONS_FILE)
doublons_keys = {
    (
        clean(d.get("reference", "")),
        clean(d.get("objet", "")),
        clean(d.get("acheteur", ""))
    )
    for d in doublons_data
}
print(clean(" 17/2025"))
# --- Chargement des consultations détaillées des deux fichiers ---
consultation_index = {}
for consult_file in CONSULT_FILES:
    consultations_data = load_jsonl(consult_file)
    for c in consultations_data:
        key = (
            clean(c.get("référence", "")),
            clean(c.get("objet", "")),
            clean(c.get("acheteur", ""))
        )
        consultation_index[key] = c  # écrasement autorisé

# --- Traitement des fichiers attributed_*.json ---
attributed_files = sorted([
    f for f in os.listdir(DAILY_DIR)
    if f.startswith("attributed_") and f.endswith(".json")
])

total_merged = 0

for filename in attributed_files:
    input_path = os.path.join(DAILY_DIR, filename)
    with open(input_path, 'r', encoding='utf-8') as f:
        try:
            attributed_data = json.load(f)
        except Exception as e:
            print(f"[❌] Erreur lecture {filename} : {e}")
            continue

    merged_data = []
    non_matched_data = []

    for attr in attributed_data:
        key = (
            clean(attr.get("reference", "")),
            clean(attr.get("objet", "")),
            clean(attr.get("acheteur", ""))
        )

        if key in doublons_keys:
            continue  # Ignorer les doublons

        consultation_match = consultation_index.get(key)
        if consultation_match:
            merged_item = {
                "reference": attr["reference"],
                "text": f"{attr['objet']} {attr['acheteur']} {consultation_match.get('lieu', '')} {consultation_match.get('catégorie', '')}".strip(),
                "nature": consultation_match.get("nature", ""),
                "montant": attr.get("montant", "")
            }
            merged_data.append(merged_item)
        else:
            non_matched_data.append(attr)

    # Écriture du fichier fusionné
    date_suffix = filename.replace("attributed_", "").replace(".json", "")

    output_path = os.path.join(OUTPUT_DIR, f"merged_output_strict_montant_{date_suffix}.jsonl")
    with open(output_path, 'w', encoding='utf-8') as out:
        for item in merged_data:
            out.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Écriture du fichier des éléments non fusionnés
    unmatched_path = os.path.join(OUTPUT_DIR, f"unmatched_output_strict_montant_{date_suffix}.jsonl")
    with open(unmatched_path, 'w', encoding='utf-8') as out:
        for item in non_matched_data:
            out.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"✅ {len(merged_data)} fusionnés | ❗ {len(non_matched_data)} non trouvés → {date_suffix}")
    total_merged += len(merged_data)

print(f"\n🎉 Fusion terminée pour tous les jours : {total_merged} éléments fusionnés.")
