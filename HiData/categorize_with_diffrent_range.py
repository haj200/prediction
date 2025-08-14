import json 
import os
import numpy as np

def categorize_data(input_file):
    # Obtenir le nom du fichier sans extension
    base_name = os.path.splitext(os.path.basename(input_file))[0]

    # Dossiers de sortie
    input_dir = os.path.dirname(os.path.abspath(input_file))
    output_root_dir = os.path.join(input_dir, base_name)
    os.makedirs(output_root_dir, exist_ok=True)

    # Charger les données depuis le fichier source
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    amounts = [item['montant'] for item in data]

    for r in range(3, 101):
        if len(amounts) < r:
            print(f"⛔ Pas assez de données pour {r} catégories (seulement {len(amounts)} éléments).")
            continue

        # Calcul des seuils
        percentiles = [100 / r * i for i in range(1, r)]
        thresholds = np.percentile(amounts, percentiles)

        # Initialiser les catégories
        categories = {f'categorie_{i+1:02d}': [] for i in range(r)}

        # Répartition
        for item in data:
            amount = item['montant']
            category_index = 0
            for i, threshold in enumerate(thresholds):
                if amount <= threshold:
                    category_index = i
                    break
                category_index = r - 1
            category_name = f'categorie_{category_index+1:02d}'
            categories[category_name].append(item)

        # Créer le dossier de sortie pour cette catégorisation
        output_dir = os.path.join(output_root_dir, f'range_{r:02d}')
        os.makedirs(output_dir, exist_ok=True)

        # Résumé de cette catégorisation
        summary = {}
        total_items = len(data)
        for category, items in categories.items():
            percentage = (len(items) / total_items) * 100 if total_items else 0
            min_amount = min((item['montant'] for item in items), default=0)
            max_amount = max((item['montant'] for item in items), default=0)
            avg_amount = sum((item['montant'] for item in items)) / len(items) if items else 0

            summary[category] = {
                "count": len(items),
                "percentage": round(percentage, 2),
                "min": round(min_amount, 2),
                "max": round(max_amount, 2),
                "mean": round(avg_amount, 2)
            }

            # Sauvegarde du fichier de catégorie
            output_file = os.path.join(output_dir, f'{category}.json')
            with open(output_file, 'w', encoding='utf-8') as cat_file:
                json.dump(items, cat_file, ensure_ascii=False, indent=2)

        # Sauvegarde du résumé JSON
        summary_file = os.path.join(output_dir, 'resume.json')
        with open(summary_file, 'w', encoding='utf-8') as summary_f:
            json.dump(summary, summary_f, ensure_ascii=False, indent=2)

        print(f"✅ Catégorisation {r} terminée et sauvegardée dans {output_dir}")

if __name__ == "__main__":
    # Définir le chemin du fichier d'entrée
    input_file = os.path.join("nature1", "nature1.json")
    
    # Vérifier si le fichier existe
    if not os.path.exists(input_file):
        print(f"❌ Le fichier {input_file} n'existe pas.")
    else:
        print(f"📂 Traitement du fichier : {input_file}")
        categorize_data(input_file) 

