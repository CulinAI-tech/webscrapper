import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
from collections import Counter
from typing import Dict, List, Tuple
from datetime import datetime

from llm_client import get_tags_from_llm
from scrappers.base import BaseScrapper

class ViiScrapper(BaseScrapper):
    def scrape(self, url, config) -> List[Dict]:
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
            

        