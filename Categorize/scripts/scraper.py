import requests
from bs4 import BeautifulSoup
import time
import random
import os
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from datetime import datetime, timedelta

# --- Configuration ---
MAX_WORKERS = 8
RETRIES = 10
TIMEOUT = 50
PAGE_SIZE = 50

BASE_URL = "https://www.marchespublics.gov.ma"
SEARCH_URL = BASE_URL + "/bdc/entreprise/consultation/resultat"

FIXED_URL_PART_1 = (
    "search_consultation_resultats%5Bkeyword%5D="
    "&search_consultation_resultats%5Breference%5D="
    "&search_consultation_resultats%5Bobjet%5D="
)
FIXED_URL_PART_2 = (
    "&search_consultation_resultats%5BdateMiseEnLigneStart%5D="
    "&search_consultation_resultats%5BdateMiseEnLigneEnd%5D="
    "&search_consultation_resultats%5Bcategorie%5D="
)
FIXED_URL_PART_3 = (
    "&search_consultation_resultats%5Bacheteur%5D="
    "&search_consultation_resultats%5Bservice%5D="
    "&search_consultation_resultats%5BlieuExecution%5D="
    f"&search_consultation_resultats%5BpageSize%5D={PAGE_SIZE}"
)

DAILY_DIR = "data_daily"
os.makedirs(DAILY_DIR, exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0"}
session = requests.Session()
session.headers.update(headers)


def get_max_page(date_str):
    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
    date_formattee = date_obj.strftime("%Y-%m-%d")
    query = (
        f"{FIXED_URL_PART_1}"
        f"&search_consultation_resultats%5BdateLimitePublicationStart%5D={date_formattee}&"
        f"search_consultation_resultats%5BdateLimitePublicationEnd%5D={date_formattee}"
        f"{FIXED_URL_PART_2}"
        f"&search_consultation_resultats%5BnaturePrestation%5D="
        f"{FIXED_URL_PART_3}"
    )
    url = f"{SEARCH_URL}?{query}"
    print(url)
    try:
        res = session.get(url, timeout=TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')
        div = soup.find('div', class_='content__resultat')
        if div:
            match = re.search(r'Nombre de résultats\s*:\s*(\d+)', div.get_text(strip=True))
            if match:
                total = int(match.group(1))
                pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
                return pages, total
    except Exception as e:
        print(f"[get_max_page] Erreur: {e}")
    return 1, 0

def extract_card_data(card):
    try:
        ref = card.select_one('.font-bold.table__links')
        objet = card.select_one('[data-bs-toggle="tooltip"]')
        buyer = card.find('span', string=lambda s: s and "Acheteur" in s)
        pub_date = card.find('span', string=lambda s: s and "Date de publication" in s)

        reference = ref.text.strip().replace('Référence :', '') if ref else None
        obj = objet.text.strip().replace('Objet :', '') if objet else None
        acheteur = buyer.parent.text.replace('Acheteur :', '').strip() if buyer else None
        date_pub = pub_date.parent.text.replace('Date de publication du résultat :', '').strip() if pub_date else None

        right = card.select_one('.entreprise__rightSubCard--top')
        if right:
            devis = right.find(string=lambda s: "Nombre de devis reçus" in s)
            nombre_devis = right.select_one("span span.font-bold").text.strip() if devis else None

            spans = right.find_all('span', recursive=False)
            attribue = False
            entreprise = montant = None

            if len(spans) >= 3:
                entreprise = spans[1].find('span', class_='font-bold')
                montant = spans[2].find('span', class_='font-bold')
                entreprise = entreprise.text.strip() if entreprise else None
                montant = montant.text.strip() if montant else None
                attribue = entreprise is not None

            return {
                "reference": reference,
                "objet": obj,
                "acheteur": acheteur,
                "date_publication": date_pub,
                "nombre_devis": nombre_devis,
                "attribue": attribue,
                "entreprise_attributaire": entreprise if attribue else None,
                "montant": montant if attribue else None
            }
    except Exception as e:
        print(f"[extract_card_data] Erreur: {e}")
    return None

def fetch_page(page, date_str):
    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
    date_formattee = date_obj.strftime("%Y-%m-%d")
    query = (
        f"{FIXED_URL_PART_1}"
        f"&search_consultation_resultats%5BdateLimitePublicationStart%5D={date_formattee}&"
        f"search_consultation_resultats%5BdateLimitePublicationEnd%5D={date_formattee}"
        f"{FIXED_URL_PART_2}"
        f"&search_consultation_resultats%5BnaturePrestation%5D="
        f"{FIXED_URL_PART_3}"
        f"&page={page}"
    )
    url = f"{SEARCH_URL}?{query}"
    for attempt in range(RETRIES):
        try:
            time.sleep(random.uniform(0.25, 0.35))
            res = session.get(url, timeout=TIMEOUT)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'lxml')
            cards = soup.select('.entreprise__card')
            return [extract_card_data(card) for card in cards if card]
        except requests.RequestException as e:
            print(f"[fetch_page] Tentative {attempt+1}/{RETRIES} - Erreur page {page}: {e}")
            time.sleep(0.3)
    return []

def save_results(data, date_str):
    attribues = [d for d in data if d and d['attribue']]
    if not attribues:
        print(f"❌ Aucune donnée attribuée trouvée pour {date_str}")
        return
    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
    file_date = date_obj.strftime("%Y-%m-%d")
    raw_path = os.path.join(DAILY_DIR, f"attributed_{file_date}.json")
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(attribues, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(attribues)} consultations attribuées sauvegardées dans {raw_path}")
    
def scrape_day(date_str):
    max_pages, total_results = get_max_page(date_str)
    print(f"🔍 {total_results} résultats trouvés sur {max_pages} pages.")
    all_data = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_page, page, date_str): page
            for page in range(1, max_pages + 1)
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc="📄 Pages"):
            result = future.result()
            if result:
                all_data.extend(result)
    print(f'📊 Total des données extraites : {len(all_data)}')
    save_results(all_data, date_str)

def loop_days(start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
    end_date = datetime.strptime(end_date_str, "%d/%m/%Y")
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%d/%m/%Y')
        print(f"\n📅 Scraping pour la date : {date_str}")
        scrape_day(date_str)
        current_date += timedelta(days=1)

if __name__ == "__main__":
    loop_days("06/07/2025", "12/07/2025")
