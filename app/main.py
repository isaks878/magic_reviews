from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Review
from app.parser import parse_ozon_reviews, extract_product_id
from app.analyzer import analyze_sentiment, fake_probability
import pandas as pd
import os

DB_FILE = os.environ.get("REVIEWS_DB", "sqlite:///reviews.db")
engine = create_engine(DB_FILE, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(engine)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

AUTH_PASS = os.environ.get("UI_PASSWORD", "ozontest")

def auth_required(request: Request):
    token = request.cookies.get("session_auth")
    if not token or token != AUTH_PASS:
        return False
    return True

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == AUTH_PASS:
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie("session_auth", value=password)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный пароль"})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not auth_required(request):
        return RedirectResponse(url="/")
    session = SessionLocal()
    data = session.query(Review).all()
    df = pd.DataFrame([{
        "Дата": r.date.strftime('%Y-%m-%d'),
        "Рейтинг": r.rating,
        "Тональность": r.sentiment,
        "Фейковость": "Да" if r.is_fake else "Нет",
        "Текст": r.text[:80]+"..."
    } for r in data])
    session.close()
    return templates.TemplateResponse("dashboard.html", {"request": request, "reviews": df.to_dict('records')})

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request, product_input: str = Form(...)):
    if not auth_required(request):
        return RedirectResponse(url="/")
    reviews_raw = parse_ozon_reviews(product_input, max_reviews=25)
    session = SessionLocal()
    for r in reviews_raw:
        sentiment = analyze_sentiment(r["text"])
        fake_prob, is_fake = fake_probability(r)
        review_obj = Review(
            product_id = extract_product_id(product_input),
            review_id = r["review_id"],
            author = r["author"],
            date = r["date"],
            rating = r["rating"],
            text = r["text"],
            sentiment = sentiment,
            fake_prob = fake_prob,
            is_fake = is_fake
        )
        session.merge(review_obj)
    session.commit()
    session.close()
    return RedirectResponse(url="/dashboard", status_code=302)
