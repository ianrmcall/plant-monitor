"""
Generate a static index.html from the current known_products.json snapshot.
Shows all in-stock plants grouped by site.
"""

import json
import os
from datetime import datetime, timezone

PRODUCTS_FILE = os.path.join(os.path.dirname(__file__), "known_products.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "index.html")


def _card(product: dict) -> str:
    genus = product["name"].split()[0]
    img_html = (
        f'<img src="{product["image_url"]}" alt="{product["name"]}">'
        if product.get("image_url")
        else '<div class="no-image">No image</div>'
    )
    return f"""
    <div class="card" data-genus="{genus}">
      <div class="card-img">{img_html}</div>
      <div class="card-body">
        <h3>{product["name"]}</h3>
        <p class="price">{product.get("price", "N/A")}</p>
        <a href="{product["product_url"]}" target="_blank" rel="noopener">View &amp; Buy</a>
      </div>
    </div>"""


def render() -> None:
    if not os.path.exists(PRODUCTS_FILE):
        print("No known_products.json found — nothing to render.")
        return

    with open(PRODUCTS_FILE) as f:
        all_products = json.load(f)

    in_stock = [p for p in all_products.values() if p.get("in_stock")]
    in_stock.sort(key=lambda p: (p["site"], p["name"]))

    by_site: dict[str, list] = {}
    for p in in_stock:
        by_site.setdefault(p["site"], []).append(p)

    updated = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    sections = ""
    if by_site:
        for site, products in sorted(by_site.items()):
            site_label = site.replace("_", " ").title()
            cards = "".join(_card(p) for p in products)
            sections += f"""
        <section>
          <h2>{site_label} <span class="count">({len(products)})</span></h2>
          <div class="grid">{cards}</div>
        </section>"""
    else:
        sections = '<p class="empty">No plants currently in stock.</p>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rare Plant Monitor</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: system-ui, sans-serif;
      background: #f4f8f4;
      color: #1a1a1a;
      margin: 0;
      padding: 0 16px 48px;
    }}
    header {{
      max-width: 900px;
      margin: 0 auto;
      padding: 32px 0 16px;
      border-bottom: 2px solid #c8e6c9;
      display: flex;
      align-items: baseline;
      gap: 16px;
      flex-wrap: wrap;
    }}
    header h1 {{ margin: 0; color: #2e7d32; font-size: 1.8rem; }}
    header .meta {{ font-size: 0.85rem; color: #777; }}
    main {{ max-width: 900px; margin: 0 auto; }}
    section {{ margin-top: 40px; }}
    h2 {{ color: #2e7d32; font-size: 1.25rem; margin-bottom: 16px; }}
    .count {{ font-weight: normal; color: #777; font-size: 1rem; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 10px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    .card-img img {{
      width: 100%;
      height: 180px;
      object-fit: cover;
      display: block;
    }}
    .no-image {{
      width: 100%;
      height: 180px;
      background: #e8f5e9;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #aaa;
      font-size: 0.9rem;
    }}
    .card-body {{
      padding: 14px;
      display: flex;
      flex-direction: column;
      flex: 1;
    }}
    .card-body h3 {{
      margin: 0 0 6px;
      font-size: 0.95rem;
      line-height: 1.4;
      flex: 1;
    }}
    .price {{
      margin: 0 0 12px;
      font-size: 1.1rem;
      font-weight: 700;
      color: #2e7d32;
    }}
    .card-body a {{
      display: inline-block;
      background: #2e7d32;
      color: #fff;
      padding: 7px 14px;
      border-radius: 6px;
      text-decoration: none;
      font-size: 0.85rem;
      font-weight: 600;
      text-align: center;
    }}
    .card-body a:hover {{ background: #1b5e20; }}
    .empty {{ color: #777; margin-top: 32px; }}
    .toggle-btn {{
      background: #e8f5e9;
      border: 2px solid #2e7d32;
      color: #2e7d32;
      padding: 6px 16px;
      border-radius: 20px;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
      transition: background 0.15s, color 0.15s;
    }}
    .toggle-btn.active {{
      background: #2e7d32;
      color: #fff;
    }}
    footer {{
      max-width: 900px;
      margin: 48px auto 0;
      font-size: 0.8rem;
      color: #aaa;
      border-top: 1px solid #e0e0e0;
      padding-top: 16px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>🌿 Rare Plant Monitor</h1>
    <span class="meta">Updated {updated} &middot; {len(in_stock)} plant(s) in stock</span>
    <button id="nicos-corner" class="toggle-btn" aria-pressed="false">🌿 Nico's Corner</button>
  </header>
  <main>{sections}</main>
  <footer>
    Monitored sites: ecuagenera.com, ecuageneraus.com, kartuz.com, andysorchids.com, lyndonlyon.com
  </footer>
  <script>
    const AROID_GENERA = new Set([
      "Aglaonema","Alocasia","Amorphophallus","Anthurium","Caladium","Colocasia",
      "Dieffenbachia","Epipremnum","Monstera","Philodendron","Pothos","Rhaphidophora",
      "Scindapsus","Spathiphyllum","Syngonium","Xanthosoma","Zamioculcas"
    ]);
    const btn = document.getElementById('nicos-corner');
    btn.addEventListener('click', () => {{
      const active = btn.classList.toggle('active');
      btn.setAttribute('aria-pressed', active);
      document.querySelectorAll('.card').forEach(card => {{
        card.style.display = (!active || AROID_GENERA.has(card.dataset.genus)) ? '' : 'none';
      }});
      document.querySelectorAll('section').forEach(section => {{
        const cards = [...section.querySelectorAll('.card')];
        const visible = cards.filter(c => c.style.display !== 'none').length;
        section.style.display = visible === 0 ? 'none' : '';
        const countEl = section.querySelector('.count');
        if (countEl) countEl.textContent = '(' + visible + ')';
      }});
    }});
  </script>
</body>
</html>
"""

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    print(f"Rendered {len(in_stock)} in-stock products to index.html")


if __name__ == "__main__":
    render()
