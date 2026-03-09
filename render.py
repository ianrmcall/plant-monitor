"""
Generate a static index.html from the current known_products.json snapshot.
Shows all in-stock plants grouped by site, with client-side filter and sort controls.

Design tokens are read from design_tokens.json (committed defaults) and injected
as CSS custom properties into the generated HTML. Run figma_sync.py first to pull
updated values from a Figma file, then re-run this script.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from filters import _GENUS_TO_FAMILY

PRODUCTS_FILE = os.path.join(os.path.dirname(__file__), "known_products.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "index.html")
TOKENS_FILE = Path(__file__).parent / "design_tokens.json"

_TOKEN_DEFAULTS: dict = {
    "colors": {
        "primary":          "#2e7d32",
        "primary-dark":     "#1b5e20",
        "primary-light":    "#e8f5e9",
        "border":           "#c8e6c9",
        "text":             "#1a1a1a",
        "text-muted":       "#777777",
        "text-placeholder": "#aaaaaa",
        "text-secondary":   "#555555",
        "surface":          "#ffffff",
        "bg-page":          "#f4f8f4",
        "bg-input":         "#fafafa",
        "border-input":     "#cccccc",
        "border-card":      "#dddddd",
        "border-footer":    "#e0e0e0",
        "text-oos":         "#888888",
    },
    "typography": {
        "font-family-base": "system-ui, sans-serif",
    },
    "layout": {
        "max-width":       "900px",
        "gap-card":        "16px",
        "gap-controls":    "20px",
        "card-img-height": "180px",
        "card-min-width":  "240px",
        "radius-card":     "10px",
        "radius-btn":      "6px",
        "radius-toggle":   "20px",
        "radius-input":    "6px",
    },
}


def _load_tokens() -> dict:
    """
    Load design_tokens.json and merge with built-in defaults.
    Values present in the file override defaults; missing keys fall back to defaults.
    """
    base: dict = {
        "colors":     dict(_TOKEN_DEFAULTS["colors"]),
        "typography": dict(_TOKEN_DEFAULTS["typography"]),
        "layout":     dict(_TOKEN_DEFAULTS["layout"]),
    }
    if TOKENS_FILE.exists():
        try:
            with TOKENS_FILE.open() as f:
                loaded = json.load(f)
            base["colors"].update(loaded.get("colors", {}))
            base["typography"].update(loaded.get("typography", {}))
            base["layout"].update(loaded.get("layout", {}))
        except json.JSONDecodeError as exc:
            print(f"Warning: design_tokens.json is malformed ({exc}) — using defaults.")
    else:
        print("Warning: design_tokens.json not found — using built-in defaults.")
    return base


def _build_root_block(tokens: dict) -> str:
    """Build a CSS :root { } block from the merged token set."""
    lines = []
    for name, value in tokens["colors"].items():
        lines.append(f"    --{name}: {value};")
    lines.append(f"    --font-family-base: {tokens['typography']['font-family-base']};")
    for name, value in tokens["layout"].items():
        lines.append(f"    --{name}: {value};")
    return ":root {{\n" + "\n".join(lines) + "\n  }}"


def _parse_price(price_str: str) -> str:
    """Extract a numeric string from a price like '$38.00'. Returns '0' if unparseable."""
    match = re.search(r"[\d]+(?:[.,]\d+)*", price_str.replace(",", ""))
    if match:
        return match.group().replace(",", "")
    return "0"


def _card(product: dict, oos: bool = False) -> str:
    genus = product["name"].split()[0]
    family = _GENUS_TO_FAMILY.get(genus, "Unknown")
    price_numeric = _parse_price(product.get("price", ""))
    img_html = (
        f'<img src="{product["image_url"]}" alt="{product["name"]}">'
        if product.get("image_url")
        else '<div class="no-image">No image</div>'
    )
    oos_attr = ' data-oos="true"' if oos else ''
    return (
        f'\n    <div class="card"{oos_attr}'
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

    out_of_stock = [p for p in all_products.values() if not p.get("in_stock")]
    out_of_stock.sort(key=lambda p: (p["site"], p["name"]))

    updated = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    all_cards = "".join(_card(p) for p in in_stock)
    all_cards += "".join(_card(p, oos=True) for p in out_of_stock)

    # Collect unique sites (sorted) to seed the JS site-checkbox list
    unique_sites = sorted({p["site"] for p in in_stock})

    # Families known from filters.py (plus "Unknown" catch-all)
    known_families = sorted(set(_GENUS_TO_FAMILY.values()))

    genus_family_js = json.dumps(_GENUS_TO_FAMILY)

    tokens = _load_tokens()
    root_block = _build_root_block(tokens)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rare Plant Monitor</title>
  <style>
    {root_block}
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: var(--font-family-base);
      background: var(--bg-page);
      color: var(--text);
      margin: 0;
      padding: 0 16px 48px;
    }}
    header {{
      max-width: var(--max-width);
      margin: 0 auto;
      padding: 32px 0 16px;
      border-bottom: 2px solid var(--border);
      display: flex;
      align-items: baseline;
      gap: 16px;
      flex-wrap: wrap;
    }}
    header h1 {{ margin: 0; color: var(--primary); font-size: 1.8rem; }}
    header .meta {{ font-size: 0.85rem; color: var(--text-muted); }}
    #controls {{
      max-width: var(--max-width);
      margin: 20px auto 0;
      padding: 16px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-card);
      display: flex;
      flex-wrap: wrap;
      gap: var(--gap-controls);
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
      color: var(--text-secondary);
    }}
    .control-group input[type="text"],
    .control-group input[type="number"],
    .control-group select {{
      border: 1px solid var(--border-input);
      border-radius: var(--radius-input);
      padding: 5px 8px;
      font-size: 0.9rem;
      color: var(--text);
      background: var(--bg-input);
      width: 100%;
    }}
    .control-group input[type="text"]:focus,
    .control-group input[type="number"]:focus,
    .control-group select:focus {{
      outline: 2px solid var(--primary);
      border-color: var(--primary);
    }}
    .price-range {{
      display: flex;
      gap: 6px;
      align-items: center;
    }}
    .price-range input {{ width: 80px; }}
    .price-range span {{ color: var(--text-muted); font-size: 0.85rem; }}
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
      color: var(--text);
      cursor: pointer;
    }}
    .sort-row {{
      display: flex;
      gap: 8px;
      align-items: center;
    }}
    #sort-dir {{
      background: var(--primary-light);
      border: 2px solid var(--primary);
      color: var(--primary);
      padding: 5px 12px;
      border-radius: var(--radius-btn);
      cursor: pointer;
      font-weight: 700;
      font-size: 0.9rem;
      white-space: nowrap;
    }}
    #sort-dir.desc {{ background: var(--primary); color: var(--surface); }}
    #clear-filters {{
      background: none;
      border: 1px solid var(--border-input);
      color: var(--text-muted);
      padding: 5px 12px;
      border-radius: var(--radius-btn);
      cursor: pointer;
      font-size: 0.85rem;
    }}
    #clear-filters:hover {{ border-color: var(--primary); color: var(--primary); }}
    main {{ max-width: var(--max-width); margin: 0 auto; }}
    section {{ margin-top: 40px; }}
    h2 {{ color: var(--primary); font-size: 1.25rem; margin-bottom: 16px; }}
    .count {{ font-weight: normal; color: var(--text-muted); font-size: 1rem; }}
    #card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(var(--card-min-width), 1fr));
      gap: var(--gap-card);
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border-card);
      border-radius: var(--radius-card);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    .card-img img {{
      width: 100%;
      height: var(--card-img-height);
      object-fit: cover;
      display: block;
    }}
    .no-image {{
      width: 100%;
      height: var(--card-img-height);
      background: var(--primary-light);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-placeholder);
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
      color: var(--primary);
    }}
    .card-body a {{
      display: inline-block;
      background: var(--primary);
      color: var(--surface);
      padding: 7px 14px;
      border-radius: var(--radius-btn);
      text-decoration: none;
      font-size: 0.85rem;
      font-weight: 600;
      text-align: center;
    }}
    .card-body a:hover {{ background: var(--primary-dark); }}
    .empty {{ color: var(--text-muted); margin-top: 32px; }}
    .toggle-btn {{
      background: var(--primary-light);
      border: 2px solid var(--primary);
      color: var(--primary);
      padding: 6px 16px;
      border-radius: var(--radius-toggle);
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
      transition: background 0.15s, color 0.15s;
    }}
    .toggle-btn.active {{
      background: var(--primary);
      color: var(--surface);
    }}
    footer {{
      max-width: var(--max-width);
      margin: 48px auto 0;
      font-size: 0.8rem;
      color: var(--text-placeholder);
      border-top: 1px solid var(--border-footer);
      padding-top: 16px;
    }}
    .section-header {{
      color: var(--primary);
      font-size: 1.25rem;
      margin: 40px 0 16px;
      font-weight: 700;
    }}
    .section-header .count {{ font-weight: normal; color: var(--text-muted); font-size: 1rem; }}
    .card[data-oos] {{
      opacity: 0.55;
      display: none;
    }}
    .card[data-oos] .card-body a {{
      background: var(--text-placeholder);
      pointer-events: none;
    }}
    .card[data-oos]::after {{
      content: "Out of Stock";
      display: block;
      text-align: center;
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--text-oos);
      padding: 4px 0 8px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
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

    <div class="control-group" style="justify-content: flex-end; gap: 8px;">
      <button id="show-oos" class="toggle-btn" aria-pressed="false">Show out of stock</button>
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
    let showOos = false;

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

    // ── Show out of stock toggle ────────────────────────────────────────────────
    document.getElementById('show-oos').addEventListener('click', () => {{
      showOos = !showOos;
      const btn = document.getElementById('show-oos');
      btn.classList.toggle('active', showOos);
      btn.setAttribute('aria-pressed', showOos);
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
      // reset OOS toggle
      showOos = false;
      document.getElementById('show-oos').classList.remove('active');
      document.getElementById('show-oos').setAttribute('aria-pressed', 'false');
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
        if (card.dataset.oos === 'true' && !showOos) return false;
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
          grid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--card-min-width),1fr));gap:var(--gap-card);margin-bottom:8px';
          siteCards.forEach(c => grid.appendChild(c));
          container.appendChild(grid);
        }});
      }} else {{
        const grid = document.createElement('div');
        grid.className = 'grid';
        grid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--card-min-width),1fr));gap:var(--gap-card);margin-top:32px';
        visible.forEach(c => grid.appendChild(c));
        container.appendChild(grid);
      }}

      const inStockVisible = visible.filter(c => c.dataset.oos !== 'true').length;
      document.getElementById('visible-count').textContent = inStockVisible;
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
