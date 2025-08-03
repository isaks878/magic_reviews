import json
import random
import time
import re
from datetime import datetime
from typing import List, Dict

import requests


# Набор user-agent'ов, чтобы не блокировали запросы
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15",
]


def extract_product_id(product_input: str) -> str:
    """Извлекает числовой ID товара из ссылки или строки."""
    if product_input.startswith("http"):
        match = re.search(r"product/(?:.*-)?(\d+)", product_input)
        if match:
            return match.group(1)
    elif product_input.isdigit():
        return product_input
    raise ValueError("Невалидный ввод")


def parse_ozon_reviews(product_input: str, max_reviews: int = 30) -> List[Dict]:
    """Получает отзывы о товаре Ozon через внутренний API."""
    pid = extract_product_id(product_input)
    reviews: List[Dict] = []
    page = 1
    session = requests.Session()
    session.trust_env = False  # ignore proxy settings that may block requests

    while len(reviews) < max_reviews:
        url = (
            "https://www.ozon.ru/api/composer-api.bx/page/json/v2?url="
            f"/product/{pid}/reviews&page={page}"
        )
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            resp = session.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError, json.JSONDecodeError):
            break

        widget_key = next(
            (k for k in data.get("widgetStates", {}) if k.startswith("webReview")),
            None,
        )
        if not widget_key:
            break
        widget_data = json.loads(data["widgetStates"][widget_key])

        for item in widget_data.get("reviews", []):
            reviews.append(
                {
                    "review_id": str(item.get("id")),
                    "author": item.get("authorText", ""),
                    "date": datetime.fromtimestamp(
                        item.get("creationTime", 0) / 1000
                    ),
                    "rating": item.get("rating", 0),
                    "text": item.get("text", ""),
                }
            )
            if len(reviews) >= max_reviews:
                break

        if not widget_data.get("paging", {}).get("nextPage"):
            break

        page += 1
        time.sleep(random.uniform(0.5, 1.5))

    return reviews

