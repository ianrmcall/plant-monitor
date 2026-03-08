import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests


def send_push(topic: str, new: list, restocked: list) -> None:
    """Send a brief push notification via ntfy.sh."""
    total = len(new) + len(restocked)
    if total == 0:
        return

    lines = [f"🌿 {total} plant alert(s) — check your email for details."]
    if new:
        lines.append(f"  • {len(new)} new listing(s)")
    if restocked:
        lines.append(f"  • {len(restocked)} back in stock")

    requests.post(
        f"https://ntfy.sh/{topic}",
        data="\n".join(lines).encode("utf-8"),
        headers={"Title": "Rare Plant Monitor"},
        timeout=10,
    )


def _product_card(product: dict, label: str) -> str:
    """Build an HTML card for one product."""
    img_html = (
        f'<img src="{product["image_url"]}" width="200" style="border-radius:6px;">'
        if product.get("image_url")
        else '<div style="width:200px;height:160px;background:#e8f5e9;'
             'display:flex;align-items:center;justify-content:center;'
             'color:#888;border-radius:6px;">No image</div>'
    )
    badge = (
        f'<span style="background:#e8f5e9;color:#2e7d32;padding:2px 8px;'
        f'border-radius:12px;font-size:12px;font-weight:600;">{label}</span>'
    )
    return f"""
    <div style="border:1px solid #ddd;border-radius:8px;padding:16px;margin:12px 0;
                display:flex;gap:16px;align-items:flex-start;background:#fff;">
      <div style="flex-shrink:0;">{img_html}</div>
      <div>
        <div style="margin-bottom:6px;">{badge}</div>
        <h3 style="margin:0 0 4px;font-size:16px;color:#1a1a1a;">{product["name"]}</h3>
        <p style="margin:0 0 4px;font-size:14px;color:#555;">
          {product.get("site", "").replace("_", " ").title()}
        </p>
        <p style="margin:0 0 12px;font-size:18px;font-weight:700;color:#2e7d32;">
          {product.get("price", "N/A")}
        </p>
        <a href="{product["product_url"]}"
           style="background:#2e7d32;color:#fff;padding:8px 16px;border-radius:6px;
                  text-decoration:none;font-size:14px;font-weight:600;">
          View &amp; Buy
        </a>
      </div>
    </div>
    """


def send_email(
    from_addr: str,
    to_addr: str,
    password: str,
    new: list,
    restocked: list,
) -> None:
    """Send an HTML digest email with all new and restocked products."""
    total = len(new) + len(restocked)
    if total == 0:
        return

    cards = ""
    if new:
        cards += "<h2 style='color:#1a1a1a;'>🌱 New Listings</h2>"
        cards += "".join(_product_card(p, "NEW") for p in new)
    if restocked:
        cards += "<h2 style='color:#1a1a1a;'>🔄 Back in Stock</h2>"
        cards += "".join(_product_card(p, "RESTOCKED") for p in restocked)

    html = f"""
    <html><body style="font-family:sans-serif;max-width:700px;margin:0 auto;padding:20px;">
      <h1 style="color:#2e7d32;">🌿 Rare Plant Monitor — {total} Alert(s)</h1>
      {cards}
      <hr style="margin-top:32px;border:none;border-top:1px solid #eee;">
      <p style="font-size:12px;color:#999;">
        Sent by your plant monitor. Sites checked:
        ecuagenera.com, ecuageneraus.com, kartuz.com, andysorchids.com, lyndonlyon.com
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🌿 Plant Monitor: {total} new alert(s)"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_addr, password)
        server.sendmail(from_addr, to_addr, msg.as_string())
