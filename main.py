"""
Rare Plant Monitor — Orchestrator

Usage:
  python main.py            # Full run: scrape, diff, notify, save state
  python main.py --dry-run  # Scrape and print results only — no writes, no notifications
"""

import sys

import config
import diff
import filters
import notify
import store
from scrapers import SCRAPERS


def main(dry_run: bool = False) -> None:
    print(f"{'[DRY RUN] ' if dry_run else ''}Starting plant monitor...\n")

    # 1. Load previous state
    known = store.load()
    print(f"  Loaded {len(known)} known products from state file.\n")

    # 2. Scrape all sites
    current: dict = {}
    for scraper in SCRAPERS:
        print(f"  Scraping {scraper.site}...")
        try:
            products = scraper.scrape()
            for p in products:
                current[p["id"]] = p
            print(f"    → {len(products)} products found")
        except Exception as e:
            print(f"    ✗ Error: {e}")

    print(f"\n  Total current products: {len(current)}\n")

    # 3. Diff
    new_products = diff.find_new(current, known)
    restocked_products = diff.find_restocked(current, known)

    print(f"  New listings:    {len(new_products)}")
    print(f"  Back in stock:   {len(restocked_products)}\n")

    # 4. Apply filters (if enabled)
    new_products = filters.apply_filters(new_products, config.FILTERS_ENABLED)
    restocked_products = filters.apply_filters(restocked_products, config.FILTERS_ENABLED)

    if config.FILTERS_ENABLED:
        print(f"  After filtering: {len(new_products)} new, {len(restocked_products)} restocked\n")

    # 5. Print results
    if new_products or restocked_products:
        if new_products:
            print("  NEW LISTINGS:")
            for p in new_products:
                print(f"    [{p['site']}] {p['name']} — {p['price']}")
                print(f"    {p['product_url']}")
        if restocked_products:
            print("\n  BACK IN STOCK:")
            for p in restocked_products:
                print(f"    [{p['site']}] {p['name']} — {p['price']}")
                print(f"    {p['product_url']}")
    else:
        print("  No new alerts this run.")

    if dry_run:
        print("\n[DRY RUN] Skipping notifications and state save.")
        return

    # 6. Notify
    if new_products or restocked_products:
        if config.NTFY_TOPIC:
            print("\n  Sending push notification...")
            try:
                notify.send_push(config.NTFY_TOPIC, new_products, restocked_products)
                print("    ✓ Push sent")
            except Exception as e:
                print(f"    ✗ Push failed: {e}")

        if config.EMAIL_FROM and config.EMAIL_PASSWORD:
            print("  Sending email...")
            try:
                notify.send_email(
                    config.EMAIL_FROM,
                    config.EMAIL_TO or config.EMAIL_FROM,
                    config.EMAIL_PASSWORD,
                    new_products,
                    restocked_products,
                )
                print("    ✓ Email sent")
            except Exception as e:
                print(f"    ✗ Email failed: {e}")

    # 7. Save updated state
    store.save(current)
    print(f"\n  State saved ({len(current)} products).")
    print("Done.")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
