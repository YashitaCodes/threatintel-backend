import csv
import os
import uuid
import random
from typing import List, Optional, Dict
from .base import DatabaseHandler

class CSVHandler(DatabaseHandler):
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        if not os.path.exists(self.csv_path):
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'id', 'title', 'content', 'snippet', 'source', 'category',
                    'date', 'author', 'sourceUrl', 'sentiment', 'sentimentScore',
                    'url'
                ])
                writer.writeheader()

    def _generate_random_sentiment(self):
        sentiment_options = ["Positive", "Neutral", "Negative"]
        sentiment = random.choice(sentiment_options)
        score = round(random.uniform(-1, 1), 2)
        return sentiment, score

    def _generate_ai_summary(self, content: str):
        return content[:100] + "..."

    async def save_article(self, article: Dict) -> str:
        sentiment, score = self._generate_random_sentiment()
        enhanced_article = {
            **article,
            'id': str(uuid.uuid4()),
            'snippet': article['content'][:150] + "...",
            'source': article['source_website'],
            'category': 'General',
            'date': article['published_date'],
            'author': 'Unknown',
            'sourceUrl': self._generate_ai_summary(article['content']),
            'sentiment': sentiment,
            'sentimentScore': score
        }
        articles = self._read_csv()
        articles.append(enhanced_article)
        self._write_csv(articles)
        return enhanced_article['id']

    async def get_article(self, article_id: str) -> Optional[Dict]:
        articles = self._read_csv()
        for article in articles:
            if article['id'] == article_id:
                return article
        return None

    async def get_articles(self, skip: int = 0, limit: int = 10) -> List[Dict]:
        articles = self._read_csv()
        return articles[skip:skip + limit]

    async def search_articles(self, query: str) -> List[Dict]:
        articles = self._read_csv()
        query = query.lower()
        return [
            article for article in articles
            if query in article['title'].lower() or query in article['content'].lower()
        ]

    async def url_exists(self, url: str) -> bool:
        articles = self._read_csv()
        return any(article['url'] == url for article in articles)

    def _read_csv(self) -> List[Dict]:
        if not os.path.exists(self.csv_path):
            return []
        with open(self.csv_path, 'r', newline='') as f:
            return list(csv.DictReader(f))

    def _write_csv(self, articles: List[Dict]):
        if articles:
            fieldnames = articles[0].keys()
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(articles)