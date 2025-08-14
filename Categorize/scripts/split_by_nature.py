import json
import os

# Charger les données
with open("merged.jsonl", "r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f]

# Dictionnaire pour regrouper par nature
nature_dict = {}
nature_id_map = {}
current_id = 1

# Regrouper les éléments par nature
for item in data:
    nature = item.get("nature", "").strip()
    
    if not nature:
        continue  # Ignore les éléments sans nature
    
    if nature not in nature_dict:
        nature_dict[nature] = []
        nature_id_map[nature] = {"id": current_id, "count": 0}
        current_id += 1
    
    nature_dict[nature].append(item)
    nature_id_map[nature]["count"] += 1

# Sauvegarder chaque groupe dans un fichier séparé
for nature, items in nature_dict.items():
    file_id = nature_id_map[nature]["id"]
    filename = f"../data/natures_new/data_nature_{file_id}.jsonl"
    
    with open(filename, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

# Sauvegarder le mapping des natures
with open("../data/natures_new/natures.json", "w", encoding="utf-8") as f:
    json.dump(nature_id_map, f, ensure_ascii=False, indent=2)

print(f"{len(nature_dict)} fichiers créés (un par nature). Détails dans natures.json")
