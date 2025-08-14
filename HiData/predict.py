import json
import spacy
from unidecode import unidecode
from pathlib import Path
import statistics

# Charger modèle spaCy
nlp = spacy.load("fr_core_news_sm")
stop_words = set(nlp.Defaults.stop_words)

def preprocess(text):
    text = unidecode(text.lower())
    doc = nlp(text)
    return set([
        token.lemma_ for token in doc
        if token.is_alpha and token.lemma_ not in stop_words
    ])

def load_price_stats(summary_path):
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    price_stats = {}
    for cat, stats in summary.items():
        price_stats[cat] = {
            'mean': stats['mean'],
            'min': stats['min'],
            'max': stats['max']
        }
    return price_stats

def predict_with_similarity(text, category_words, multiple=False, tolerance=2):
    processed = preprocess(text)
    similarities = {
        category: len(processed.intersection(set(words)))
        for category, words in category_words.items()
    }
    sorted_similarities = sorted(similarities.items(), key=lambda x: x[1], reverse=True)

    if not multiple or len(sorted_similarities) < 2:
        return [sorted_similarities[0]]

    first, second = sorted_similarities[0], sorted_similarities[1]
    if abs(first[1] - second[1]) <= tolerance:
        return [first, second]
    return [first]

def analyze_file_with_rank(json_path, rank, use_multiple=False, tolerance=2):
    print(f"\nAnalyse du fichier : {json_path.name} avec rang : {rank}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rang = str(rank).zfill(2)
    category_dir = Path("data_categories") / rang

    with open(category_dir / "processed_categories.json", "r", encoding="utf-8") as f:
        category_words = json.load(f)
    price_stats = load_price_stats(category_dir / "resume_categories.json")

    results = []
    errors = []
    error_percentages = []

    all_prices = [float(str(d['montant']).replace(',', '.')) for d in data]

    for i, item in enumerate(data, 1):
        try:
            real_price = float(str(item['montant']).replace(',', '.'))
            full_text = item.get('objet', '') + ' ' + item.get('description', '')
            predictions = predict_with_similarity(full_text, category_words, use_multiple, tolerance)

            entry_result = {
                'id': item.get('id', f"elt_{i}"),
                'real_price': real_price,
                'predictions': []
            }

            for cat, score in predictions:
                cat_stats = price_stats[cat]
                diff = abs(real_price - cat_stats['mean'])
                err_percent = (diff / real_price) * 100 if real_price else 0
                count_in_range = sum(1 for p in all_prices if cat_stats['min'] <= p <= cat_stats['max'])

                entry_result['predictions'].append({
                    'category': cat,
                    'similarity_score': score,
                    'predicted_avg_price': cat_stats['mean'],
                    'min': cat_stats['min'],
                    'max': cat_stats['max'],
                    'price_difference': diff,
                    'error_percentage': err_percent,
                    'count_in_predicted_range': count_in_range
                })

                if predictions.index((cat, score)) == 0:
                    errors.append(diff)
                    error_percentages.append(err_percent)

            results.append(entry_result)

        except Exception as e:
            print(f"Erreur avec l'élément {i}: {e}")
            continue

    stats = {
        'nb_total': len(results),
        'erreur_moyenne': statistics.mean(errors) if errors else 0,
        'erreur_mediane': statistics.median(errors) if errors else 0,
        'erreur_moyenne_%': statistics.mean(error_percentages) if error_percentages else 0,
        'erreur_mediane_%': statistics.median(error_percentages) if error_percentages else 0
    }

    final_report = {
        'statistiques_globales': stats,
        'predictions_detaillees': results
    }

    output_path = category_dir / f"rapport_prediction_{json_path.stem}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Rapport généré : {output_path}")
    print(f"   Erreur moyenne : {stats['erreur_moyenne']:.2f} MAD ({stats['erreur_moyenne_%']:.2f}%)")
    print(f"   Erreur médiane : {stats['erreur_mediane']:.2f} MAD ({stats['erreur_mediane_%']:.2f}%)")

    return final_report

# --- Lancement interactif ---
if __name__ == "__main__":
    chemin_fichier = input("Chemin du fichier JSON à analyser (ex: data_cleaned/25.json) : ").strip()
    rang = input("Rang de catégorisation (ex: 25) : ").strip()
    choix = input("Activer l’option de catégories proches ? (o/n) : ").strip().lower()
    use_multiple = choix == 'o'
    tolerance = 2
    if use_multiple:
        tol_input = input("Tolérance pour similarité proche (ex: 2) [défaut=2] : ").strip()
        if tol_input.isdigit():
            tolerance = int(tol_input)

    json_path = Path(chemin_fichier)
    if json_path.exists():
        analyze_file_with_rank(json_path, rang, use_multiple, tolerance)
    else:
        print(f"❌ Fichier introuvable : {chemin_fichier}")
