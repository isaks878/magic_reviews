import re

def analyze_sentiment(text: str) -> str:
    pos = ['отлично','рекомендую','супер','доволен']
    neg = ['плохо','ужасно','отвратительно','разочарован','не рекомендую']
    p = sum(word in text.lower() for word in pos)
    n = sum(word in text.lower() for word in neg)
    if p > n:
        return "positive"
    elif n > p:
        return "negative"
    else:
        return "neutral"

def fake_probability(review):
    score = 0
    if len(review['text']) < 15: score += 0.3
    if 'рекомендую' in review['text'].lower() and len(review['text']) < 40: score += 0.2
    if re.match(r'^\W+$', review['author']): score += 0.2
    if score > 0.5:
        return score, True
    return score, False
