import re

from bs4 import BeautifulSoup

from .base import BaseScraper

BASE = "https://www.kartuz.com"

CATEGORY_PAGES = [
    "/c/1GES/Gesneriads.html",
    "/c/2BEG/Begonias.html",
    "/c/7RFP/Rare+Flowering+Plants.html",
    "/c/8FLV/Vines+and+Climbers.html",
    "/c/8Y01/Other+Categories.html",
]


class KartuzScraper(BaseScraper):
    site = "kartuz"

    def scrape(self) -> list[dict]:
        products = []
        for i, path in enumerate(CATEGORY_PAGES, 1):
            url = BASE + path
            print(f"    [kartuz] category {i}/{len(CATEGORY_PAGES)}: {path}")
            try:
                soup = BeautifulSoup(self.get(url).text, "html.parser")
                products.extend(self._parse_category(soup, url))
            except Exception as e:
                print(f"    [kartuz] Error fetching {url}: {e}")
        return products

    def _parse_category(self, soup: BeautifulSoup, page_url: str) -> list[dict]:
        """
        Kartuz lists products inline as text blocks. Each product has the pattern:
          <b>Plant Name</b>
          Code: XXXXX
          Price: $XX.XX
          Quantity in Basket: none   ← in stock indicator
        """
        products = []
        # Find all bold tags — product names are in <b> tags followed by code/price
        text = soup.get_text(separator="\n")
        # Split on "Quantity:" to get individual product blocks
        blocks = re.split(r"Quantity(?:\s+in\s+Basket)?:", text)

        for block in blocks:
            code_match = re.search(r"Code:\s*(\S+)", block)
            price_match = re.search(r"Price:\s*(\$[\d.]+)", block)
            if not code_match or not price_match:
                continue

            code = code_match.group(1)
            price = price_match.group(1)

            # Name: text before "Code:" on same line or preceding non-empty line
            before_code = block[: code_match.start()].strip()
            lines = [l.strip() for l in before_code.split("\n") if l.strip()]
            name = lines[-1] if lines else "Unknown"
            # Strip any trailing punctuation artifacts
            name = re.sub(r"\s+", " ", name).strip()

            # Stock: block that follows "Quantity in Basket:" contains "none" if in stock
            in_stock = "none" in block[: price_match.start()].lower()

            # Images not available on listing pages — use empty string
            products.append({
                "id": f"{self.site}:{code}",
                "site": self.site,
                "name": name,
                "price": price,
                "image_url": "",
                "product_url": page_url,
                "in_stock": in_stock,
            })
        return products
