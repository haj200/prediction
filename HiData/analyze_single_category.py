import json
import spacy
import os
from unidecode import unidecode

# Charger le modèle spaCy pour le français
nlp = spacy.load('fr_core_news_sm')

# Mots vides à exclure
stop_words = set(nlp.Defaults.stop_words)

def normalize_text(text):
    """Minuscule + suppression des accents"""
    text = text.lower()
    text = unidecode(text)
    return text

def process_category_file(file_path, fields_to_use):
    """
    Traite un seul fichier JSON de catégorie.
    - file_path : chemin du fichier JSON
    - fields_to_use : liste des champs à concaténer (ex: ["objet", "reference", "acheteur"])
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_words = []

    for item in data:
        # Concaténer les champs spécifiés
        texts = [item.get(field, "") for field in fields_to_use if isinstance(item.get(field, ""), str)]
        combined_text = " ".join(texts)
        combined_text = normalize_text(combined_text)

        # Traitement NLP avec spaCy
        doc = nlp(combined_text)

        # Lemmatisation + filtrage
        words = [token.lemma_ for token in doc
                 if token.lemma_ not in stop_words
                 and token.is_alpha
                 and len(token.lemma_) > 1]

        all_words.extend(words)

    unique_sorted_words = sorted(set(all_words))
    return unique_sorted_words

def process_all_ranges(base_dir, fields_to_use):
    """
    Traite toutes les catégories dans tous les dossiers de range
    - base_dir : chemin du dossier principal (ex: 'nature1/nature1')
    - fields_to_use : liste des champs à analyser
    """
    # Parcourir tous les sous-dossiers
    for range_dir in os.listdir(base_dir):
        if not range_dir.startswith('range_'):
            continue

        range_path = os.path.join(base_dir, range_dir)
        if not os.path.isdir(range_path):
            continue

        print(f"📂 Traitement du dossier : {range_dir}")

        # Dictionnaire pour stocker les résultats de toutes les catégories de ce range
        range_results = {
            "metadata": {
                "range_name": range_dir,
                "fields_analyzed": fields_to_use
            },
            "categories": {}
        }

        # Traiter chaque fichier de catégorie
        for file in os.listdir(range_path):
            if not file.startswith('categorie_') or not file.endswith('.json'):
                continue

            category_name = file[:-5]  # Enlever le '.json'
            category_path = os.path.join(range_path, file)
            print(f"  📄 Analyse de : {file}")

            # Traiter le fichier
            words = process_category_file(category_path, fields_to_use)
            
            # Ajouter les résultats au dictionnaire
            range_results["categories"][category_name] = {
                "word_count": len(words),
                "words": words
            }

        # Sauvegarder les résultats dans un seul fichier pour ce range
        output_filename = f"analysis_{range_dir}.json"
        output_path = os.path.join(range_path, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(range_results, f, ensure_ascii=False, indent=2)

        print(f"✅ Analyse terminée pour {range_dir} - Résultats sauvegardés dans {output_filename}")

if __name__ == "__main__":
    # Configuration
    base_dir = os.path.join("nature1", "nature1")
    fields_to_use = ["objet", "reference", "acheteur"]  # Ajustez selon vos besoins

    # Vérifier si le dossier existe
    if not os.path.exists(base_dir):
        print(f"❌ Le dossier {base_dir} n'existe pas.")
    else:
        print(f"🔍 Début de l'analyse pour : {base_dir}")
        process_all_ranges(base_dir, fields_to_use)
        print("✨ Traitement terminé !")

