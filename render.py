"""
Generate a static index.html from the current known_products.json snapshot.
Shows all in-stock plants grouped by site, with client-side filter and sort controls.
"""

import json
import os
import re
from datetime import datetime, timezone

from filters import _GENUS_TO_FAMILY

PRODUCTS_FILE = os.path.join(os.path.dirname(__file__), "known_products.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "index.html")


def _parse_price(price_str: str) -> str:
    """Extract a numeric string from a price like '$38.00'. Returns '0' if unparseable."""
    match = re.search(r"[\d]+(?:[.,]\d+)*", price_str.replace(",", ""))
    if match:
        return match.group().replace(",", "")
    return "0"


def _card(product: dict) -> str:
    genus = product["name"].split()[0]
    family = _GENUS_TO_FAMILY.get(genus, "Unknown")
    price_numeric = _parse_price(product.get("price", ""))
    img_html = (
        f'<img src="{product["image_url"]}" alt="{product["name"]}">'
        if product.get("image_url")
        else '<div class="no-image">No image</div>'
    )
    return (
        f'\n    <div class="card"'
        f' data-genus="{genus}"'
        f' data-site="{product["site"]}"'
        f' data-price="{price_numeric}"'
        f' data-family="{family}">'
        f'\n      <div class="card-img">{img_html}</div>'
        f'\n      <div class="card-body">'
        f'\n        <h3>{product["name"]}</h3>'
        f'\n        <p class="price">{product.get("price", "N/A")}</p>'
        f'\n        <a href="{product["product_url"]}" target="_blank" rel="noopener">View &amp; Buy</a>'
        f'\n      </div>'
        f'\n    </div>'
    )


def render() -> None:
    if not os.path.exists(PRODUCTS_FILE):
        print("No known_products.json found — nothing to render.")
        return

    with open(PRODUCTS_FILE) as f:
        all_products = json.load(f)

    in_stock = [p for p in all_products.values() if p.get("in_stock")]
    in_stock.sort(key=lambda p: (p["site"], p["name"]))

    updated = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    all_cards = "".join(_card(p) for p in in_stock)

    # Collect unique sites (sorted) to seed the JS site-checkbox list
    unique_sites = sorted({p["site"] for p in in_stock})

    # Families known from filters.py (plus "Unknown" catch-all)
    known_families = sorted(set(_GENUS_TO_FAMILY.values()))

    genus_family_js = json.dumps(_GENUS_TO_FAMILY)

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
    #controls {{
      max-width: 900px;
      margin: 20px auto 0;
      padding: 16px;
      background: #fff;
      border: 1px solid #c8e6c9;
      border-radius: 10px;
      display: flex;
      flex-wrap: wrap;
      gap: 20px;
      align-items: flex-start;
    }}
    .control-group {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 140px;
    }}
    .control-group label,
    .control-group .group-label {{
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #555;
    }}
    .control-group input[type="text"],
    .control-group input[type="number"],
    .control-group select {{
      border: 1px solid #ccc;
      border-radius: 6px;
      padding: 5px 8px;
      font-size: 0.9rem;
      color: #1a1a1a;
      background: #fafafa;
      width: 100%;
    }}
    .control-group input[type="text"]:focus,
    .control-group input[type="number"]:focus,
    .control-group select:focus {{
      outline: 2px solid #2e7d32;
      border-color: #2e7d32;
    }}
    .price-range {{
      display: flex;
      gap: 6px;
      align-items: center;
    }}
    .price-range input {{ width: 80px; }}
    .price-range span {{ color: #777; font-size: 0.85rem; }}
    .site-checks {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .site-checks label {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.88rem;
      font-weight: normal;
      text-transform: none;
      letter-spacing: 0;
      color: #1a1a1a;
      cursor: pointer;
    }}
    .sort-row {{
      display: flex;
      gap: 8px;
      align-items: center;
    }}
    #sort-dir {{
      background: #e8f5e9;
      border: 2px solid #2e7d32;
      color: #2e7d32;
      padding: 5px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 700;
      font-size: 0.9rem;
      white-space: nowrap;
    }}
    #sort-dir.desc {{ background: #2e7d32; color: #fff; }}
    #clear-filters {{
      background: none;
      border: 1px solid #ccc;
      color: #777;
      padding: 5px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.85rem;
    }}
    #clear-filters:hover {{ border-color: #2e7d32; color: #2e7d32; }}
    main {{ max-width: 900px; margin: 0 auto; }}
    section {{ margin-top: 40px; }}
    h2 {{ color: #2e7d32; font-size: 1.25rem; margin-bottom: 16px; }}
    .count {{ font-weight: normal; color: #777; font-size: 1rem; }}
    #card-grid {{
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
    .section-header {{
      color: #2e7d32;
      font-size: 1.25rem;
      margin: 40px 0 16px;
      font-weight: 700;
    }}
    .section-header .count {{ font-weight: normal; color: #777; font-size: 1rem; }}
  </style>
</head>
<body>
  <header>
    <h1>🌿 Rare Plant Monitor</h1>
    <span class="meta">Updated {updated} &middot; <span id="visible-count">{len(in_stock)}</span> plant(s) in stock</span>
    <button id="nicos-corner" class="toggle-btn" aria-pressed="false">🌿 Nico's Corner</button>
  </header>

  <div id="controls">
    <div class="control-group">
      <span class="group-label">Website</span>
      <div class="site-checks" id="site-checks">
        <!-- populated by JS -->
      </div>
    </div>

    <div class="control-group">
      <label for="genus-filter">Genus</label>
      <input type="text" id="genus-filter" placeholder="e.g. Monstera" autocomplete="off">
    </div>

    <div class="control-group">
      <label for="family-filter">Family</label>
      <select id="family-filter">
        <option value="">All families</option>
        {''.join(f'<option value="{f}">{f}</option>' for f in known_families)}
        <option value="Unknown">Unknown</option>
      </select>
    </div>

    <div class="control-group">
      <span class="group-label">Price</span>
      <div class="price-range">
        <input type="number" id="price-min" placeholder="Min" min="0" step="1">
        <span>&ndash;</span>
        <input type="number" id="price-max" placeholder="Max" min="0" step="1">
      </div>
    </div>

    <div class="control-group">
      <span class="group-label">Sort</span>
      <div class="sort-row">
        <select id="sort-by">
          <option value="site-name">Website &amp; Name</option>
          <option value="name">Name</option>
          <option value="price">Price</option>
          <option value="genus">Genus</option>
          <option value="family">Family</option>
        </select>
        <button id="sort-dir" title="Toggle sort direction">↑ Asc</button>
      </div>
    </div>

    <div class="control-group" style="justify-content: flex-end;">
      <button id="clear-filters">Clear filters</button>
    </div>
  </div>

  <main>
    <div id="card-container">
      <div id="card-grid">{all_cards}
      </div>
    </div>
  </main>

  <footer>
    Monitored sites: ecuagenera.com, ecuageneraus.com, kartuz.com, andysorchids.com, lyndonlyon.com
  </footer>

  <script>
    const GENUS_TO_FAMILY = {genus_family_js};

    // ── State ──────────────────────────────────────────────────────────────────
    const allCards = Array.from(document.querySelectorAll('#card-grid .card'));
    let sortAsc = true;

    // ── Build website checkboxes from actual data ───────────────────────────────
    const uniqueSites = [...new Set(allCards.map(c => c.dataset.site))].sort();
    const siteChecks = document.getElementById('site-checks');
    uniqueSites.forEach(site => {{
      const label = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.value = site;
      cb.checked = true;
      cb.addEventListener('change', applyFiltersAndSort);
      label.appendChild(cb);
      label.appendChild(document.createTextNode(' ' + site.replace(/_/g, ' ')));
      siteChecks.appendChild(label);
    }});

    // ── Sort direction toggle ──────────────────────────────────────────────────
    const sortDirBtn = document.getElementById('sort-dir');
    sortDirBtn.addEventListener('click', () => {{
      sortAsc = !sortAsc;
      sortDirBtn.textContent = sortAsc ? '↑ Asc' : '↓ Desc';
      sortDirBtn.classList.toggle('desc', !sortAsc);
      applyFiltersAndSort();
    }});

    // ── Clear filters ──────────────────────────────────────────────────────────
    document.getElementById('clear-filters').addEventListener('click', () => {{
      document.querySelectorAll('#site-checks input[type=checkbox]').forEach(cb => cb.checked = true);
      document.getElementById('genus-filter').value = '';
      document.getElementById('family-filter').value = '';
      document.getElementById('price-min').value = '';
      document.getElementById('price-max').value = '';
      document.getElementById('sort-by').value = 'site-name';
      sortAsc = true;
      sortDirBtn.textContent = '↑ Asc';
      sortDirBtn.classList.remove('desc');
      // reset Nico's Corner
      const ncBtn = document.getElementById('nicos-corner');
      ncBtn.classList.remove('active');
      ncBtn.setAttribute('aria-pressed', 'false');
      applyFiltersAndSort();
    }});

    // ── Nico's Corner shortcut ─────────────────────────────────────────────────
    const ncBtn = document.getElementById('nicos-corner');
    ncBtn.addEventListener('click', () => {{
      const active = ncBtn.classList.toggle('active');
      ncBtn.setAttribute('aria-pressed', active);
      const familySelect = document.getElementById('family-filter');
      familySelect.value = active ? 'Araceae' : '';
      applyFiltersAndSort();
    }});

    // ── Core filter + sort ─────────────────────────────────────────────────────
    function applyFiltersAndSort() {{
      const checkedSites = new Set(
        [...document.querySelectorAll('#site-checks input:checked')].map(cb => cb.value)
      );
      const genusQuery = document.getElementById('genus-filter').value.trim().toLowerCase();
      const familyFilter = document.getElementById('family-filter').value;
      const priceMin = parseFloat(document.getElementById('price-min').value);
      const priceMax = parseFloat(document.getElementById('price-max').value);
      const sortBy = document.getElementById('sort-by').value;

      // 1. Filter
      const visible = allCards.filter(card => {{
        if (!checkedSites.has(card.dataset.site)) return false;
        if (genusQuery && !card.dataset.genus.toLowerCase().includes(genusQuery)) return false;
        if (familyFilter && card.dataset.family !== familyFilter) return false;
        const price = parseFloat(card.dataset.price);
        if (!isNaN(priceMin) && price < priceMin) return false;
        if (!isNaN(priceMax) && price > priceMax) return false;
        return true;
      }});

      // 2. Sort
      const dir = sortAsc ? 1 : -1;
      visible.sort((a, b) => {{
        let va, vb;
        switch (sortBy) {{
          case 'price':
            va = parseFloat(a.dataset.price);
            vb = parseFloat(b.dataset.price);
            return dir * (va - vb);
          case 'genus':
            va = a.dataset.genus.toLowerCase();
            vb = b.dataset.genus.toLowerCase();
            break;
          case 'family':
            va = a.dataset.family.toLowerCase();
            vb = b.dataset.family.toLowerCase();
            break;
          case 'name':
            va = a.querySelector('h3').textContent.toLowerCase();
            vb = b.querySelector('h3').textContent.toLowerCase();
            break;
          case 'site-name':
          default:
            va = a.dataset.site + '\x00' + a.querySelector('h3').textContent.toLowerCase();
            vb = b.dataset.site + '\x00' + b.querySelector('h3').textContent.toLowerCase();
            break;
        }}
        if (va < vb) return -dir;
        if (va > vb) return dir;
        return 0;
      }});

      // 3. Render — group by site when sorted by site-name, else flat
      const container = document.getElementById('card-container');
      container.innerHTML = '';

      if (visible.length === 0) {{
        container.innerHTML = '<p class="empty">No plants match the current filters.</p>';
        document.getElementById('visible-count').textContent = '0';
        return;
      }}

      const groupBySite = (sortBy === 'site-name');

      if (groupBySite) {{
        const groups = {{}};
        visible.forEach(card => {{
          const site = card.dataset.site;
          if (!groups[site]) groups[site] = [];
          groups[site].push(card);
        }});
        Object.keys(groups).sort().forEach(site => {{
          const siteCards = groups[site];
          const h = document.createElement('h2');
          h.className = 'section-header';
          h.innerHTML = site.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) +
            ' <span class="count">(' + siteCards.length + ')</span>';
          container.appendChild(h);
          const grid = document.createElement('div');
          grid.className = 'grid';
          grid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-bottom:8px';
          siteCards.forEach(c => grid.appendChild(c));
          container.appendChild(grid);
        }});
      }} else {{
        const grid = document.createElement('div');
        grid.className = 'grid';
        grid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-top:32px';
        visible.forEach(c => grid.appendChild(c));
        container.appendChild(grid);
      }}

      document.getElementById('visible-count').textContent = visible.length;
    }}

    // ── Event listeners ────────────────────────────────────────────────────────
    document.getElementById('genus-filter').addEventListener('input', applyFiltersAndSort);
    document.getElementById('family-filter').addEventListener('change', () => {{
      // sync Nico's Corner button
      const familyVal = document.getElementById('family-filter').value;
      const ncBtn = document.getElementById('nicos-corner');
      const isAraceae = familyVal === 'Araceae';
      ncBtn.classList.toggle('active', isAraceae);
      ncBtn.setAttribute('aria-pressed', isAraceae);
      applyFiltersAndSort();
    }});
    document.getElementById('price-min').addEventListener('input', applyFiltersAndSort);
    document.getElementById('price-max').addEventListener('input', applyFiltersAndSort);
    document.getElementById('sort-by').addEventListener('change', applyFiltersAndSort);

    // ── Initial render ─────────────────────────────────────────────────────────
    applyFiltersAndSort();
  </script>
</body>
</html>
"""

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    print(f"Rendered {len(in_stock)} in-stock products to index.html")


if __name__ == "__main__":
    render()
