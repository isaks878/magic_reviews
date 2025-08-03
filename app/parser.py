import json
import random
import time
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Настройка логирования для парсера
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Набор user-agent'ов, чтобы не блокировали запросы
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
]

def _build_headers() -> Dict[str, str]:
    """Собирает заголовки, имитирующие реальные запросы браузера."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.ozon.ru/",
    }


def extract_product_id(product_input: str) -> str:
    """Извлекает числовой ID товара из ссылки или строки."""
    if product_input.startswith("http"):
        match = re.search(r"product/(?:.*-)?(\d+)", product_input)
        if match:
            return match.group(1)
    elif product_input.isdigit():
        return product_input
    raise ValueError("Невалидный ввод: имена или ссылки без ID не поддерживаются")


def parse_ozon_reviews(
    product_input: str, max_reviews: Optional[int] = None
) -> List[Dict]:
    """Получает отзывы о товаре Ozon через внутренний API с логированием процесса."""
    pid = extract_product_id(product_input)
    logger.info("Начинаем загрузку отзывов для товара %s", pid)
    reviews: List[Dict] = []
    page = 1

    session = requests.Session()
    session.trust_env = False  # игнорируем системные прокси

    # Настраиваем повторы при сетевых ошибках
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    while True:
        if max_reviews is not None and len(reviews) >= max_reviews:
            logger.info("Достигнуто максимальное число отзывов: %d", max_reviews)
            break

        url = (
            "https://www.ozon.ru/api/composer-api.bx/page/json/v2?url="
            f"/product/{pid}/reviews&page={page}"
        )
        try:
            resp = session.get(url, headers=_build_headers(), timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
            logger.exception(
                "Ошибка при загрузке страницы %s для товара %s: %s", page, pid, exc
            )
            break

        widget_key = next(
            (k for k in data.get("widgetStates", {}) if k.startswith("webReview")),
            None,
        )
        if not widget_key:
            logger.warning("Не найден ключ веб-виджета на странице %s для товара %s", page, pid)
            break

        widget_data = json.loads(data["widgetStates"][widget_key])

        for item in widget_data.get("reviews", []):
            reviews.append(
                {
                    "review_id": str(item.get("id")),
                    "author": item.get("authorText", ""),
                    "date": datetime.fromtimestamp(item.get("creationTime", 0) / 1000),
                    "rating": item.get("rating", 0),
                    "text": item.get("text", ""),
                }
            )
            if max_reviews is not None and len(reviews) >= max_reviews:
                break

        if not widget_data.get("paging", {}).get("nextPage"):
            logger.info(
                "Страниц больше нет (последняя страница %s) для товара %s", page, pid
            )
            break

        page += 1
        time.sleep(random.uniform(1, 2))

    logger.info("Загружено %d отзывов для товара %s", len(reviews), pid)
    return reviews