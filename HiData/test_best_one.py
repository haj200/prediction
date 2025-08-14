import json
import spacy
from unidecode import unidecode
from pathlib import Path

# Charger le modèle NLP français
nlp = spacy.load("fr_core_news_sm")
stop_words = set(nlp.Defaults.stop_words)

def preprocess(text):
    text = unidecode(text.lower())
    doc = nlp(text)
    return set([
        token.lemma_ for token in doc
        if token.is_alpha and token.lemma_ not in stop_words
    ])

def predict_category(text, categories_data):
    processed = preprocess(text)
    similarities = {}
    
    for cat_name, cat_data in categories_data.items():
        words = set(cat_data['words'])  # Convertir en set pour une recherche plus rapide
        common = processed.intersection(words)
        score = len(common)
        similarities[cat_name] = score
    
    return max(similarities, key=similarities.get)

def load_category_data(data_path):
    # Extraire le rang du chemin (ex: "03" de "range_03")
    range_number = data_path.name.split('_')[1]
    
    # Chargement des fichiers de catégories et du résumé
    categories_data = {}
    
    # Charger le résumé pour obtenir les statistiques
    with open(data_path / "resume.json", "r", encoding="utf-8") as f:
        price_stats = json.load(f)
    
    # Charger l'analyse qui contient les mots par catégorie
    with open(data_path / f"analysis_range_{range_number}.json", "r", encoding="utf-8") as f:
        analysis_data = json.load(f)
    
    # Combiner les données
    for cat_name in price_stats.keys():
        categories_data[cat_name] = {
            'words': analysis_data['categories'][cat_name]['words'],
            'stats': price_stats[cat_name]
        }
    
    return categories_data

def predict_from_user_input(range_label):
    print("\n--- Prédiction d'une catégorie pour un nouvel enregistrement ---")
    
    objet = input("Objet : ").strip()
    acheteur = input("Acheteur : ").strip()
    reference = input("Référence : ").strip()

    # Construction du texte à analyser
    fields = [objet, acheteur, reference]
    text = ' '.join([f for f in fields if f != ''])
    
    if not text:
        print("Aucune donnée saisie. Abandon.")
        return

    # Construire le chemin vers le dossier range_XX
    data_path = Path(f"nature1/nature1/range_{range_label}")
    
    if not data_path.exists():
        print(f"Erreur : Le dossier {data_path} n'existe pas.")
        return

    # Charger les données nécessaires pour la prédiction
    try:
        categories_data = load_category_data(data_path)
    except Exception as e:
        print(f"Erreur lors du chargement des données : {e}")
        return

    # Prédire la catégorie
    predicted_cat = predict_category(text, categories_data)
    stats = categories_data[predicted_cat]['stats']
    
    print(f"\nCatégorie prédite : {predicted_cat}")
    print(f"→ Prix moyen : {stats['mean']} MAD")
    print(f"→ Plage de prix : [{stats['min']} MAD, {stats['max']} MAD]")
    print(f"→ Nombre d'entrées dans cette catégorie : {stats['count']}")
    print(f"→ Pourcentage du total : {stats['percentage']}%")

# Exemple d'utilisation
if __name__ == "__main__":
    # Ex : pour une catégorisation en 12 classes -> data_categories/12/
    rang = input("Entrer le rang de catégorisation (ex: 12, 25, 50...) : ").strip()
    if not rang.isdigit():
        print("Valeur invalide pour le rang.")
    else:
        range_label = rang.zfill(2)  # 4 → "04", 12 → "12"
        predict_from_user_input(range_label)
