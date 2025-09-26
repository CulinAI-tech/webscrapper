import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
from collections import Counter
from typing import Dict, List, Tuple
from datetime import datetime

from llm_client import get_tags_from_llm
from llm_client import get_normalized_name
from scrappers.base import BaseScrapper

class IncorrecteScrapper(BaseScrapper):
    def scrape(self, url, config) -> List[Dict]:
        menu = []
        current_dish = {}
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resposta = requests.get(url, headers=headers)
            if resposta.status_code != 200:
                return []
            soup = BeautifulSoup(resposta.text, "html.parser")

            items = soup.select("h2.elementor-heading-title")

            for h2 in items:
                text = h2.get_text(strip=True)

                if text.endswith("€"):  
                    # tanca plat
                    current_dish["price"] = text
                    full_text = current_dish.get("name", "") + " " + current_dish.get("description", "")
                    full_text = full_text.strip()
                    
                    # Llamada LLM
                    normalized_text = get_normalized_name(full_text)
                    print(f"Procesant plat: {normalized_text}")
                    tags, ingredients = get_tags_from_llm(normalized_text)

                    menu.append({
                        "plat": normalized_text,
                        "preu": current_dish["price"],
                        "ingredients": ingredients,
                        "tags": tags,
                        "scraped_at": datetime.now().isoformat()
                    })

                    current_dish = {}
                else:
                    # assigna nom o descrició
                    if "name" not in current_dish:
                        current_dish["name"] = text
                    else:
                        current_dish["description"] = current_dish.get("description", "") + " " + text

        except Exception as e:
            print(f"[ERROR] {url}: {e}")
            return []

        return menu
