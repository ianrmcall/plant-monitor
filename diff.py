def find_new(current: dict, known: dict) -> list:
    """Return products that have never been seen before."""
    return [p for pid, p in current.items() if pid not in known]


def find_restocked(current: dict, known: dict) -> list:
    """Return products that were out of stock last run and are now available."""
    restocked = []
    for pid, p in current.items():
        if pid in known and not known[pid].get("in_stock") and p.get("in_stock"):
            restocked.append(p)
    return restocked
