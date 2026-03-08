import os

from dotenv import load_dotenv

load_dotenv()


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


NTFY_TOPIC = get("NTFY_TOPIC")
EMAIL_FROM = get("EMAIL_FROM")
EMAIL_TO = get("EMAIL_TO")
EMAIL_PASSWORD = get("EMAIL_PASSWORD")
FILTERS_ENABLED = get("FILTERS_ENABLED", "false").lower() == "true"
