import json
import csv
import time
import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
from collections import Counter
from typing import Dict, List, Tuple
import sqlite3
from datetime import datetime

# Selenium opcional
from selenium import webdriver
from selenium.webdriver.common.by import By

# PDF
import fitz  # PyMuPDF

# Carregar configuració i restaurants
with open("config.json", "r", encoding="utf-8") as f:
    configs = json.load(f)

with open("urls.json", "r", encoding="utf-8") as f:
    restaurants = json.load(f)

LLM_URL = "http://localhost:8080/api/llm/query"

def get_tags_from_llm(plat_text: str) -> Tuple[List[str], List[str]]:
    """
    Demana al LLM els tags per un plat.
    Retorna una tupla (tags, ingredients).
    """
    prompt = f"""
        Ets un expert en gastronomia. Analitza el següent plat i genera una llista de tags rellevants:
        - Categoria (aperitiu, plat principal, postres, etc.)
        - Identificació del tipus de plat (sopa, amanida, carn, peix, pasta, etc.)
        - Ingredients principals
        - Tipus de dieta (vegà, vegetarià, sense gluten, etc.)

        Retorna només un JSON amb clau "tags", amb una llista de strings i una clau "ingredients" amb els ingredients principals com una llista de strings.

        Plat: "{plat_text}"
        """

    payload = {"prompt": prompt}
    try:
        resp = requests.post(LLM_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            # Agafem el camp "answer"
            answer = resp.json().get("answer", "")
            # Netejar ```json ... ``` i tot abans/després
            m = re.search(r'\{.*\}', answer, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                tags = data.get("tags", [])
                ingredients = data.get("ingredients", [])
                return tags, ingredients
            else:
                print(f"[LLM WARNING] No s'ha trobat JSON a la resposta per: {plat_text}")
        else:
            print(f"[LLM ERROR] Status {resp.status_code} per: {plat_text}")
    except Exception as e:
        print(f"[LLM ERROR] {e} per: {plat_text}")
    return [], []

def scrape_restaurant(url: str, config: Dict) -> List[Dict]:
    """Scrapa un restaurant i retorna la llista de plats amb tags i ingredients."""
    menu = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resposta = requests.get(url, headers=headers)
        
        if resposta.status_code != 200:
            return []

        soup = BeautifulSoup(resposta.text, "html.parser")
        

        # Buscar contenidor i items
        container = soup.select_one(config["container_selector"])
        if not container:
            print("[!] No s'ha trobat el contenidor")
            return []
        

        items = container.select(config["item_selector"])
        

        for p in items:
            text = p.get_text(" ", strip=True)
            match = re.search(config["plat_preu_regex"], text)
            if match:
                plat = match.group(1).strip()
                preu = match.group(2).strip()

                detall = ""
                if "span_detall_class" in config:
                    span = p.find("span", class_=config["span_detall_class"])
                    detall = span.get_text(strip=True) if span else ""

                full_text = f"{plat} {detall}".strip()
                tags, ingredients = get_tags_from_llm(full_text)  # Corregit!
                
                menu.append({
                    "plat": full_text,
                    "preu": preu,
                    "ingredients": ingredients,  # Llista
                    "tags": tags,  # Llista
                    "scraped_at": datetime.now().isoformat()
                })
            else:
                print("Sense match:", text)

    except Exception as e:
        print(f"[ERROR] {url}: {e}")
        return []

    return menu

def find_pdf_url(page_url):
    """Troba un enllaç a un PDF dins la pàgina donada."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://macarraca.com/"
    }
    resp = requests.get(page_url, headers=headers)
    #resp = requests.get(page_url, timeout=10)
    print("status: ", resp.status_code)
    if resp.status_code != 200:
        print("[ERROR] No s’ha pogut obrir la pàgina")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Buscar <a> amb href que acabi en .pdf
    link = soup.find("a", href=re.compile(r"\.pdf$"))
    if link:
        return link["href"]

    # Buscar <object data="...pdf">
    obj = soup.find("object", {"data": re.compile(r"\.pdf$")})
    if obj:
        return obj["data"]

    return None

def scrape_pdf(url: str, config: Dict) -> List[Dict]:
    """Scrapa un PDF i retorna la llista de plats amb tags i ingredients."""
    pdf_url = find_pdf_url(url)
    if pdf_url:
        print("Trobada carta en PDF:", pdf_url)
        plats = scrape_pdf(pdf_url, config["plat_regex"])
        for p in plats:
            print(p)
    else:
        print("No s’ha trobat PDF")
    menu = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resposta = requests.get(url, headers=headers)
        print("Status:", resposta.status_code)
        if resposta.status_code != 200:
            return []

        # Guardar PDF temporalment
        with open("temp.pdf", "wb") as f:
            f.write(resposta.content)

        # Obrir PDF amb fitz
        doc = fitz.open("temp.pdf")
        text = ""
        for page in doc:
            text += page.get_text()

        # Processar línies
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            match = re.match(r"^([A-Za-zÀ-ÖØ-öø-ÿ0-9 ,.'-]+)\s+([0-9]+(\\.[0-9]{1,2})?€)$", line)
            if match:
                plat = match.group(1).strip()
                preu = match.group(2).strip()
                tags, ingredients = get_tags_from_llm(plat)  # Corregit!
                
                menu.append({
                    "plat": plat,
                    "preu": preu,
                    "ingredients": ingredients,  # Llista
                    "tags": tags,  # Llista
                    "scraped_at": datetime.now().isoformat()
                })
            else:
                print("Sense match al PDF:", line)

    except Exception as e:
        print(f"[ERROR PDF] {url}: {e}")
        return []

    return menu

# EXECUCIÓ PRINCIPAL
def main():
    all_menus = []
    
    # Scraping
    for r in restaurants:
        url = r["url"]
        nom = r["nom"]
        conf_name = r["config"]
        config = configs[conf_name]
        print(f"Scraping {nom} ({url})...")
        
        if conf_name == "vii":
            menu = scrape_restaurant(url, config)  
        elif conf_name == "pdf":
            menu = scrape_pdf(url, config)
        if conf_name == "incorrecte":
            menu = scrape_restaurant(url, config)            
        else:
            print(f"⚠️ Tipus de config desconegut: {conf_name}")
            continue

        if not menu:
            print(f"No s'ha trobat informació per {nom}")
        else:
            all_menus.append({
                'restaurant': nom,
                'dishes': menu
            })
        
        time.sleep(2)  # evitar bloquejos
    
    # Guardar a CSV tradicional (per compatibilitat)
    with open("menus.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Restaurant", "Plat", "Preu", "Tags", "Ingredients", "Scraped_At"])
        
        for menu_data in all_menus:
            for item in menu_data['dishes']:
                writer.writerow([
                    menu_data['restaurant'], 
                    item["plat"], 
                    item["preu"], 
                    ",".join(item["tags"]),
                    ",".join(item["ingredients"]),
                    item["scraped_at"]
                ])
    

if __name__ == "__main__":
    main()
    print("\nScraping i anàlisi complets!")