import json
import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "known_products.json")


def load() -> dict:
    """Load previously seen products from the state file."""
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)


def save(products: dict) -> None:
    """Save the current product snapshot to the state file."""
    with open(STATE_FILE, "w") as f:
        json.dump(products, f, indent=2)
