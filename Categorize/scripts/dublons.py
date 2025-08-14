import json
import os
from collections import defaultdict

# --- Configuration ---
DAILY_DIR = "data_daily"
OUTPUT_FILE = "doublons.jsonl"

# --- Chargement des fichiers JSON quotidiens ---
files = [f for f in os.listdir(DAILY_DIR) if f.startswith("attributed_") and f.endswith(".json")]

# --- Indexation des enregistrements ---
seen = defaultdict(list)

for filename in files:
    full_path = os.path.join(DAILY_DIR, filename)
    with open(full_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[⚠️] Erreur de lecture JSON dans {filename} : {e}")
            continue

        for record in data:
            if not record:
                continue
            try:
                key = (
                    record["reference"].strip().lower(),
                    record["objet"].strip().lower(),
                    record["acheteur"].strip().lower()
                )
                seen[key].append(record)
            except Exception as e:
                print(f"[⚠️] Erreur sur un enregistrement de {filename} : {e}")

# --- Sauvegarde des doublons ---
with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    doublons_count = 0
    for group in seen.values():
        if len(group) > 1:
            for item in group:
                out.write(json.dumps(item, ensure_ascii=False) + "\n")
            doublons_count += 1

print(f"✅ {doublons_count} groupes de doublons écrits dans '{OUTPUT_FILE}'")
