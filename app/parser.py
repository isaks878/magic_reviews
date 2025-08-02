from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time, re
from datetime import datetime

def extract_product_id(product_input: str) -> str:
    if product_input.startswith('http'):
        match = re.search(r'product/(\d+)', product_input)
        if match:
            return match.group(1)
    elif product_input.isdigit():
        return product_input
    else:
        raise ValueError("Невалидный ввод")
    return product_input

def parse_ozon_reviews(product_input: str, max_reviews=30) -> list:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    pid = extract_product_id(product_input)
    url = f"https://www.ozon.ru/product/{pid}/reviews"

    driver.get(url)
    time.sleep(2)

    reviews = []
    count = 0
    while count < max_reviews:
        review_blocks = driver.find_elements(By.CSS_SELECTOR, '[data-widget="webReview"]')
        for rb in review_blocks:
            try:
                rating = float(rb.find_element(By.CSS_SELECTOR, '[data-test-id="review-rating-value"]').text.replace(',','.'))
                text = rb.find_element(By.CSS_SELECTOR, '[data-test-id="review-text"]').text.strip()
                author = rb.find_element(By.CSS_SELECTOR, '[data-test-id="review-author-name"]').text.strip()
                date_str = rb.find_element(By.CSS_SELECTOR, '[data-test-id="review-date"]').text.strip()
                date = datetime.strptime(date_str, "%d %B %Y")
                reviews.append({
                    "review_id": f"rev_{count}_{pid}",
                    "author": author,
                    "date": date,
                    "rating": rating,
                    "text": text
                })
                count += 1
            except Exception as err:
                continue
            if count >= max_reviews:
                break
        # Кнопка "Следующая страница"
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, '[data-test-id="pagination-forward"]')
            if 'disabled' in next_btn.get_attribute('class'):
                break
            next_btn.click()
            time.sleep(2)
        except Exception:
            break
    driver.quit()
    return reviews
