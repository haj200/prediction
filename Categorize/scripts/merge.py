import os
import json

# --- Configuration ---
DAILY_DIR = "data_daily"
OUTPUT_FILE = "merged_attributed.jsonl"

# --- Filtrage des fichiers à fusionner ---
files = sorted([
    f for f in os.listdir(DAILY_DIR)
    if f.startswith("attributed_") and f.endswith(".json")
])

total_records = 0

# --- Fusion des fichiers ---
with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
    for file in files:
        full_path = os.path.join(DAILY_DIR, file)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for record in data:
                    outfile.write(json.dumps(record, ensure_ascii=False) + "\n")
                    total_records += 1
        except Exception as e:
            print(f"❌ Erreur dans le fichier {file} : {e}")

print(f"✅ Fusion terminée : {total_records} enregistrements écrits dans {OUTPUT_FILE}")
