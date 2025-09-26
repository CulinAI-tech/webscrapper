from typing import Dict, List

class BaseScrapper:
    def scrape(self, url: str, config: Dict) -> List[Dict]:
        """Mètode comú a tots els scrapers"""
        raise NotImplementedError("Aquest scraper no està implementat")
