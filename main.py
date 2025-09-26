import csv, time, json
from scrappers.pdf_scrapper import PdfScrapper
from scrappers.vii_scrapper import ViiScrapper
from scrappers.incorrecte_scrapper import IncorrecteScrapper

# carregar config
with open("config.json", encoding="utf-8") as f:
    configs = json.load(f)
with open("urls.json", encoding="utf-8") as f:
    restaurants = json.load(f)

SCRAPPERS = {
    "pdf": PdfScrapper(),
    "vii": ViiScrapper(),    
    "incorrecte": IncorrecteScrapper()
}

def main():
    all_menus = []
    for r in restaurants:
        scrapper = SCRAPPERS.get(r["config"])
        if not scrapper:
            print(f"⚠️ No hi ha scraper per {r['config']}")
            continue

        print(f"Scraping {r['nom']} ({r['url']}) amb {r['config']}...")
        menu = scrapper.scrape(r["url"], configs[r["config"]])
        if menu:
            all_menus.append({"restaurant": r["nom"], "dishes": menu})
        time.sleep(2)

    # guardar CSV
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
