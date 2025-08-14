import requests
from bs4 import BeautifulSoup
import concurrent.futures
import time
import os
import json
import threading

BASE_URL = "https://www.marchespublics.gov.ma/bdc/entreprise/consultation/show/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_RETRIES = 20
TIMEOUT = 60
MAX_WORKERS = 10

lock = threading.Lock()
output_path = os.path.join("data_daily", "consultations.ndjson")  # newline-delimited JSON

def fetch_and_parse(id_):
    url = f"{BASE_URL}{id_}"
    session = requests.Session()
    session.headers.update(HEADERS)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            h4 = soup.find("h4")
            objet_tag = soup.find("span", class_="text-black")
            if not h4 or not objet_tag:
                print(f"[{id_}] Page sans contenu structuré.")
                return None

            reference = h4.text.strip()
            objet = objet_tag.text.strip()

            details = soup.find_all("div", class_="d-flex flex-column")
            if len(details) < 6:
                print(f"[{id_}] Détails incomplets.")
                return None

            acheteur = details[0].find_all("span")[1].text.strip()
            date_mise_en_ligne = details[1].find_all("span")[1].text.strip()
            date_limite = details[2].find_all("span")[1].text.strip()
            lieu = details[3].find_all("span")[1].text.strip()
            categorie = details[4].find_all("span")[1].text.strip()
            nature = details[5].find_all("span")[1].text.strip()

            articles = []
            accordion_items = soup.find_all("div", class_="accordion-item")
            for item in accordion_items:
                titre = item.find("button", class_="accordion-button").get_text(strip=True)
                sous_cartes = item.find_all("div", class_="content__article--subMiniCard")
                quantite = sous_cartes[1].text.strip() if len(sous_cartes) > 1 else "N/A"
                articles.append({
                    "titre": titre,
                    "quantité": quantite
                })

            return {
                "id": id_,
                "référence": reference,
                "objet": objet,
                "acheteur": acheteur,
                "date_mise_en_ligne": date_mise_en_ligne,
                "date_limite": date_limite,
                "lieu": lieu,
                "catégorie": categorie,
                "nature": nature,
                "articles": articles
            }

        except requests.RequestException as e:
            print(f"[{id_}] Échec tentative {attempt}: {e}")
            time.sleep(1)

    print(f"[{id_}] Abandon après {MAX_RETRIES} tentatives.")
    return None


def write_result(result):
    with lock:
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")


def main():
    os.makedirs("data_daily", exist_ok=True)
    # Si fichier existe, on le vide d'abord
    open(output_path, "w", encoding="utf-8").close()

    start_id = 215533
    end_id = 219782
    valid_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_id = {executor.submit(fetch_and_parse, i): i for i in range(start_id, end_id + 1)}

        for future in concurrent.futures.as_completed(future_to_id):
            result = future.result()
            if result:
                write_result(result)
                valid_count += 1
                print(f"[{result['id']}] ✅")

    print(f"\n✅ Total consultations valides récupérées : {valid_count}")


if __name__ == "__main__":
    main()
