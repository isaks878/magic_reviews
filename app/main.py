from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Review
from app.parser import parse_ozon_reviews, extract_product_id
from app.analyzer import analyze_sentiment, fake_probability
import pandas as pd
import os
import logging

# Настройка логирования
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("app.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
logger = logging.getLogger(__name__)

# Настройка базы данных
DB_FILE = os.environ.get("REVIEWS_DB", "sqlite:///reviews.db")
engine = create_engine(DB_FILE, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(engine)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    session = SessionLocal()
    data = session.query(Review).all()
    df = pd.DataFrame([
        {
            "Дата": r.date.strftime("%Y-%m-%d"),
            "Рейтинг": r.rating,
            "Тональность": r.sentiment,
            "Фейковость": "Да" if r.is_fake else "Нет",
            "Текст": r.text[:80] + "...",
        }
        for r in data
    ])
    session.close()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "reviews": df.to_dict("records"),
            "error": request.query_params.get("error"),
        },
    )

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request, product_input: str = Form(...)):
    logger.info("Fetching reviews for %s", product_input)
    reviews_raw = parse_ozon_reviews(product_input, max_reviews=25)
    if not reviews_raw:
        logger.warning("No reviews fetched for %s", product_input)
        return RedirectResponse(
            url="/?error=Не удалось получить отзывы", status_code=302
        )
    logger.info("Got %d reviews for %s", len(reviews_raw), product_input)

    session = SessionLocal()
    for r in reviews_raw:
        sentiment = analyze_sentiment(r["text"])
        fake_prob, is_fake = fake_probability(r)
        review_obj = Review(
            product_id=extract_product_id(product_input),
            review_id=r["review_id"],
            author=r["author"],
            date=r["date"],
            rating=r["rating"],
            text=r["text"],
            sentiment=sentiment,
            fake_prob=fake_prob,
            is_fake=is_fake,
        )
        session.merge(review_obj)
    session.commit()
    session.close()
    return RedirectResponse(url="/", status_code=302)
