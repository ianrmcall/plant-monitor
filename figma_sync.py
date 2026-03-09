"""
Sync design tokens from a Figma file into design_tokens.json.

Reads color styles, text styles, and variables from your Figma file and
overwrites the matching entries in design_tokens.json. Tokens not found in
Figma are left at their existing values (never deleted).

Setup:
  1. Create a personal access token at Figma → Settings → Personal access tokens
  2. Copy the file key from your Figma file URL:
       https://www.figma.com/file/{FILE_KEY}/Your-File-Name
  3. Set FIGMA_TOKEN and FIGMA_FILE_KEY in your .env file
  4. Run: python figma_sync.py

Figma naming conventions:
  Color styles  : "Primary", "Primary Dark", "Surface", "Text Muted", etc.
                  Group prefixes like "Brand/" are stripped automatically.
                  Style names are slugified: "Primary Dark" → "primary-dark"
  Text styles   : Name one style "Font Family Base" (or any name slugifying to
                  "font-family-base") to set the base font.
  Variables     : Name them to match layout token slugs: "max-width",
                  "gap-card", "radius-card", etc. FLOAT variables get a "px"
                  suffix; STRING variables are used as-is.

IMPORTANT: design_tokens.json is committed to the repo and serves as the
fallback when Figma credentials are not available. Always commit it after
running this script.
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

FIGMA_TOKEN = os.environ.get("FIGMA_TOKEN", "")
FIGMA_FILE_KEY = os.environ.get("FIGMA_FILE_KEY", "")
TOKENS_FILE = Path(__file__).parent / "design_tokens.json"
API_BASE = "https://api.figma.com/v1"
TIMEOUT = 15


# ── Helpers ────────────────────────────────────────────────────────────────────

def rgba_to_hex(r: float, g: float, b: float, a: float = 1.0) -> str:
    """Convert Figma's 0–1 float RGBA to a CSS hex string."""
    ri, gi, bi = (round(c * 255) for c in (r, g, b))
    if a < 1.0:
        ai = round(a * 255)
        return f"#{ri:02x}{gi:02x}{bi:02x}{ai:02x}"
    return f"#{ri:02x}{gi:02x}{bi:02x}"


def slugify(name: str) -> str:
    """
    Convert a Figma style/variable name to a CSS-variable-friendly slug.
    Strips group prefix ("Brand/Primary Dark" → "Primary Dark"),
    lowercases, and replaces non-alphanumeric runs with hyphens.
    """
    leaf = name.rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "-", leaf.lower()).strip("-")


def figma_get(path: str) -> dict:
    """GET a Figma API endpoint and return the parsed JSON."""
    url = f"{API_BASE}/{path}"
    try:
        resp = requests.get(
            url,
            headers={"X-Figma-Token": FIGMA_TOKEN},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        print(f"Network error fetching {url}: {exc}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code == 403:
        print(
            "ERROR: Figma returned 403. Check that FIGMA_TOKEN is valid and "
            "has read access to the file.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        print(f"HTTP error fetching {url}: {exc}", file=sys.stderr)
        sys.exit(1)

    return resp.json()


# ── Sync logic ─────────────────────────────────────────────────────────────────

def sync_styles(tokens: dict) -> int:
    """
    Fetch color and text styles from Figma and update tokens in-place.
    Returns the number of tokens updated.
    """
    data = figma_get(f"files/{FIGMA_FILE_KEY}/styles")
    styles = data.get("meta", {}).get("styles", [])

    if not styles:
        print("No styles found in Figma file — color/typography tokens unchanged.")
        return 0

    color_styles = [s for s in styles if s.get("style_type") == "FILL"]
    text_styles  = [s for s in styles if s.get("style_type") == "TEXT"]

    all_style_ids = [s["node_id"] for s in color_styles + text_styles]
    if not all_style_ids:
        return 0

    nodes_data = figma_get(
        f"files/{FIGMA_FILE_KEY}/nodes?ids={','.join(all_style_ids)}"
    )
    nodes = nodes_data.get("nodes", {})

    updated = 0
    slug_seen: dict[str, str] = {}

    # Color styles
    for style in color_styles:
        slug = slugify(style["name"])
        if slug in slug_seen:
            print(
                f"WARNING: Duplicate slug '{slug}' from Figma styles "
                f"'{slug_seen[slug]}' and '{style['name']}' — skipping the second."
            )
            continue
        slug_seen[slug] = style["name"]

        node = nodes.get(style["node_id"], {}).get("document", {})
        fills = node.get("fills", [])
        if not fills:
            print(f"WARNING: Style '{style['name']}' has no fills — skipped.")
            continue
        fill = fills[0]
        if fill.get("type") != "SOLID":
            print(
                f"WARNING: Style '{style['name']}' is not a solid fill "
                f"(type={fill.get('type')}) — skipped."
            )
            continue

        color = fill["color"]
        hex_val = rgba_to_hex(color["r"], color["g"], color["b"], color.get("a", 1.0))

        if color.get("a", 1.0) < 1.0:
            print(
                f"WARNING: Style '{style['name']}' has alpha < 1 — "
                f"stored as 8-digit hex ({hex_val})."
            )

        if slug in tokens["colors"]:
            tokens["colors"][slug] = hex_val
            updated += 1
        else:
            print(
                f"INFO: Figma style '{style['name']}' (slug '{slug}') "
                "does not match any token — ignored."
            )

    # Text styles (font-family only)
    for style in text_styles:
        slug = slugify(style["name"])
        node = nodes.get(style["node_id"], {}).get("document", {})
        font_family = node.get("style", {}).get("fontFamily")
        if not font_family:
            continue

        font_stack = f"{font_family}, system-ui, sans-serif"
        typo_slug = "font-family-base"
        if slug == typo_slug or slug == "font-family":
            tokens["typography"]["font-family-base"] = font_stack
            updated += 1
        else:
            print(
                f"INFO: Text style '{style['name']}' (slug '{slug}') "
                "does not match any typography token — ignored."
            )

    return updated


def sync_variables(tokens: dict) -> int:
    """
    Fetch Figma Variables and update layout tokens in-place.
    Returns the number of tokens updated.
    """
    data = figma_get(f"files/{FIGMA_FILE_KEY}/variables/local")
    variables = data.get("variables", {})

    if not variables:
        print("No variables found in Figma file — layout tokens unchanged.")
        return 0

    updated = 0
    for var in variables.values():
        name = var.get("name", "")
        slug = slugify(name)
        var_type = var.get("resolvedType", "")

        # Variables can have per-mode values; use the first available value
        value_by_mode = var.get("valuesByMode", {})
        if not value_by_mode:
            continue
        raw = next(iter(value_by_mode.values()))

        if var_type == "FLOAT":
            css_value = f"{raw}px" if isinstance(raw, (int, float)) else str(raw)
        elif var_type == "STRING":
            css_value = str(raw)
        else:
            continue  # COLOR and BOOLEAN variables not handled here

        if slug in tokens["layout"]:
            tokens["layout"][slug] = css_value
            updated += 1
        else:
            print(
                f"INFO: Figma variable '{name}' (slug '{slug}') "
                "does not match any layout token — ignored."
            )

    return updated


def main() -> None:
    if not FIGMA_TOKEN:
        print(
            "ERROR: FIGMA_TOKEN is not set. Add it to your .env file.\n"
            "  Get a token at Figma → Settings → Personal access tokens",
            file=sys.stderr,
        )
        sys.exit(1)
    if not FIGMA_FILE_KEY:
        print(
            "ERROR: FIGMA_FILE_KEY is not set. Add it to your .env file.\n"
            "  Copy the key from your Figma file URL:\n"
            "  https://www.figma.com/file/{FILE_KEY}/Your-File-Name",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load existing tokens as the base (never start from scratch)
    if TOKENS_FILE.exists():
        with TOKENS_FILE.open() as f:
            tokens = json.load(f)
        print(f"Loaded existing tokens from {TOKENS_FILE.name}")
    else:
        print(f"WARNING: {TOKENS_FILE.name} not found — starting from empty token set.")
        tokens = {"colors": {}, "typography": {}, "layout": {}}

    print(f"\nFetching styles from Figma file '{FIGMA_FILE_KEY}'...")
    style_updates = sync_styles(tokens)

    print(f"Fetching variables from Figma file '{FIGMA_FILE_KEY}'...")
    var_updates = sync_variables(tokens)

    total = style_updates + var_updates
    if total == 0:
        print("\nNo token values were updated — design_tokens.json was not modified.")
        return

    with TOKENS_FILE.open("w") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        f"\nSaved {total} updated token(s) to {TOKENS_FILE.name} "
        f"({style_updates} from styles, {var_updates} from variables).\n"
        "Run 'python render.py' to regenerate index.html with the new design."
    )


if __name__ == "__main__":
    main()
