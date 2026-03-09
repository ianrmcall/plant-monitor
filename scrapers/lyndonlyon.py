import re
import urllib3

from bs4 import BeautifulSoup

from .base import BaseScraper

# Lyndon Lyon's SSL certificate is expired/self-signed — suppress the warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://lyndonlyon.com/store"

# cPath values for each category — discovered by browsing the store nav
CATEGORY_PATHS = {
    "african_violets": 1,
    "gesneriads": 2,
    "other_plants": 3,
    "new_listings": 35,
}


class LyndonLyonScraper(BaseScraper):
    site = "lyndonlyon"

    def scrape(self) -> list[dict]:
        products = []
        seen_ids = set()
        for category, cpath in CATEGORY_PATHS.items():
            page = 1
            while True:
                try:
                    url = f"{BASE}/index.php"
                    soup = BeautifulSoup(
                        self.get(url, params={"main_page": "index", "cPath": cpath, "page": page}, verify=False).text,
                        "html.parser",
                    )
                    page_products = self._parse_listing(soup)
                    if not page_products:
                        break  # No more pages
                    for p in page_products:
                        if p["id"] not in seen_ids:
                            seen_ids.add(p["id"])
                            products.append(p)
                    page += 1
                except Exception as e:
                    print(f"[lyndonlyon] Error scraping cPath={cpath} page={page}: {e}")
                    break
        return products

    def _parse_listing(self, soup: BeautifulSoup) -> list[dict]:
        products = []
        # Zen Cart table layout: tr.productListing-odd / productListing-even
        for row in soup.find_all("tr", class_=re.compile(r"productListing-(odd|even)")):
            # Name + product URL: h3.itemTitle > a
            title_tag = row.select_one("h3.itemTitle a")
            if not title_tag:
                continue

            href = title_tag.get("href", "")
            pid_match = re.search(r"products_id=(\d+)", href)
            if not pid_match:
                continue

            pid = pid_match.group(1)
            name = title_tag.get_text(strip=True)

            # Price: span.productPrices
            price = ""
            price_tag = row.select_one("span.productPrices")
            if price_tag:
                price_match = re.search(r"\$[\d,]+\.?\d*", price_tag.get_text())
                price = price_match.group(0) if price_match else ""

            # Image: img.listingProductImage
            image_url = ""
            img = row.select_one("img.listingProductImage")
            if img and img.get("src"):
                src = img["src"]
                image_url = src if src.startswith("http") else f"{BASE}/{src.lstrip('/')}"

            # Stock: "Add to Cart" span present = in stock
            in_stock = bool(row.select_one("span.button_buy_now"))

            products.append({
                "id": f"{self.site}:{pid}",
                "site": self.site,
                "name": name,
                "price": price,
                "image_url": image_url,
                "product_url": href,
                "in_stock": in_stock,
            })
        return products
