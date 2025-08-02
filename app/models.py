from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    product_id = Column(String)
    review_id = Column(String)
    author = Column(String)
    date = Column(DateTime)
    rating = Column(Float)
    text = Column(String)
    sentiment = Column(String)
    fake_prob = Column(Float)
    is_fake = Column(Boolean)