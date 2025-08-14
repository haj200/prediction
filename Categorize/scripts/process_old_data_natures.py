import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from string import punctuation
from nltk.corpus import stopwords

# === PARAMÈTRES ===
FICHIER_INTERVALS = "C:/Users/pc/Desktop/NewData/data/intervals.json"
DOSSIER_DATA = "C:/Users/pc/Desktop/NewData/data/natures"  # contient les fichiers data_nature_xx.jsonl
DOSSIER_SORTIE = "C:/Users/pc/Desktop/NewData/data/resultats_par_nature"
FICHIER_INTERVALS_OUT = "intervalles.json"

# === STOPWORDS FRANÇAIS ===
STOPWORDS = set(stopwords.words('french'))


def normalize_text(text):
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(rf"[{punctuation}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def convertir_montant(montant_str):
    montant_str = montant_str.replace("MAD", "").replace(",", ".").replace(" ", "").strip()
    try:
        return float(montant_str)
    except ValueError:
        return None


def charger_intervalles(fichier):
    print(f"Chargement des intervalles depuis {fichier}...")
    with open(fichier, "r", encoding="utf-8") as f:
        config = json.load(f)

    intervalles = []
    for bloc in config:
        min_, max_, step = bloc["min"], bloc["max"], bloc["step"]
        val = min_
        while val < max_:
            intervalles.append((val, val + step))
            val += step

    print(f"{len(intervalles)} intervalles chargés.")
    return intervalles


def get_interval(montant, intervalles):
    for interval in intervalles:
        if interval[0] <= montant < interval[1]:
            return f"{interval[0]}-{interval[1]}"
    return None


def traiter_fichier(fichier_path, intervalles, regroupement):
    print(f"Traitement du fichier : {fichier_path.name}")
    lignes = 0
    valides = 0
    with open(fichier_path, "r", encoding="utf-8") as f:
        for line in f:
            lignes += 1
            try:
                data = json.loads(line)
                montant = convertir_montant(data.get("montant", ""))
                nature = data.get("nature", "").strip()
                texte = data.get("text", "")

                if montant is None or not nature or not texte:
                    continue

                interval = get_interval(montant, intervalles)
                if not interval:
                    continue

                regroupement[nature][interval].append(texte)
                valides += 1
            except json.JSONDecodeError:
                continue
    print(f"  -> {valides}/{lignes} enregistrements valides ajoutés.")


def extraire_mots_uniques(textes):
    mots = set()
    for texte in textes:
        texte = normalize_text(texte)
        for mot in texte.split():
            if mot not in STOPWORDS and len(mot) > 2:
                mots.add(mot)
    return sorted(mots)


def main():
    # Créer dossier sortie s'il n'existe pas
    Path(DOSSIER_SORTIE).mkdir(parents=True, exist_ok=True)

    # Charger intervalles
    intervalles = charger_intervalles(FICHIER_INTERVALS)

    # Sauvegarder intervalles pour vérification
    with open(FICHIER_INTERVALS_OUT, "w", encoding="utf-8") as f_out:
        json.dump([{"min": i[0], "max": i[1]} for i in intervalles], f_out, indent=2)

    regroupement = defaultdict(lambda: defaultdict(list))

    # Traiter tous les fichiers
    fichiers = list(Path(DOSSIER_DATA).glob("data_nature_*.jsonl"))
    if not fichiers:
        print("Aucun fichier trouvé dans", DOSSIER_DATA)
        return

    for fichier in fichiers:
        traiter_fichier(fichier, intervalles, regroupement)

    # Pour chaque nature, stocker séparément les résultats
    for nature, interv_data in regroupement.items():
        print(f"Traitement de la nature : {nature}")
        resultats = {}
        for interval, textes in interv_data.items():
            mots_uniques = extraire_mots_uniques(textes)
            if mots_uniques:  # Ne rien écrire si vide
                resultats[interval] = mots_uniques

        if resultats:
            nom_fichier = f"{nature.replace(' ', '_').replace('/', '_')}.json"
            chemin_fichier = Path(DOSSIER_SORTIE) / nom_fichier
            with open(chemin_fichier, "w", encoding="utf-8") as f_out:
                json.dump(resultats, f_out, indent=2, ensure_ascii=False)
            print(f"  -> Résultats enregistrés dans {chemin_fichier}")
        else:
            print(f"  -> Aucun mot utile trouvé pour {nature}, rien sauvegardé.")


if __name__ == "__main__":
    main()
