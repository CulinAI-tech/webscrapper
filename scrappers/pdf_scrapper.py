import requests
import fitz
import re
from datetime import datetime
from typing import Dict, List
from llm_client import get_tags_from_llm
from scrappers.base import BaseScrapper

class PdfScrapper(BaseScrapper):
    def scrape(self, url: str, config: Dict) -> List[Dict]:
        menu = []
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return []
        
        with open("temp.pdf", "wb") as f:
            f.write(resp.content)

        doc = fitz.open("temp.pdf")
        text = "\n".join(page.get_text() for page in doc)
        lines = text.split("\n")

        for line in lines:
            match = re.match(config["plat_preu_regex"], line.strip())
            if match:
                plat = match.group(1).strip()
                preu = match.group(2).strip()
                tags, ingredients = get_tags_from_llm(plat)
                menu.append({
                    "plat": plat,
                    "preu": preu,
                    "tags": tags,
                    "ingredients": ingredients,
                    "scraped_at": datetime.now().isoformat()
                })
        fitz.close()
        doc.close()
        fitz.delete("temp.pdf")
        return menu
