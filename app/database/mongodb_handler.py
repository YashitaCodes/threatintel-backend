from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import List, Optional, Dict
import random
from .base import DatabaseHandler

class MongoDBHandler(DatabaseHandler):
    def __init__(self, mongodb_uri: str, database_name: str):
        self.client = AsyncIOMotorClient(mongodb_uri)
        self.db = self.client[database_name]
        self.collection = self.db.articles

    def _generate_random_sentiment(self):
        sentiment_options = ["Positive", "Neutral", "Negative"]
        sentiment = random.choice(sentiment_options)
        score = round(random.uniform(-1, 1), 2)
        return sentiment, score

    def _generate_ai_summary(self, content: str):
        # Simulate AI summary with first 100 characters
        return content[:100] + "..."

    async def save_article(self, article: Dict) -> str:
        # Add the new required fields
        sentiment, score = self._generate_random_sentiment()
        enhanced_article = {
            **article,
            'id': ObjectId().__str__(),  # Use string representation of ObjectId as id
            'snippet': article['content'][:150] + "...",
            'category': 'General',  # Default category
            'author': 'Unknown',  # Default author
            'sourceUrl': self._generate_ai_summary(article['content']),
            'sentiment': sentiment,
            'sentimentScore': score
        }
        result = await self.collection.insert_one(enhanced_article)
        return str(result.inserted_id)

    async def get_article(self, article_id: str) -> Optional[Dict]:
        article = await self.collection.find_one({"_id": ObjectId(article_id)})
        if article:
            article["_id"] = str(article["_id"])
        return article

    async def get_articles(self, skip: int = 0, limit: int = 10) -> List[Dict]:
        cursor = self.collection.find().skip(skip).limit(limit)
        articles = []
        async for article in cursor:
            article["_id"] = str(article["_id"])
            articles.append(article)
        return articles

    async def search_articles(self, query: str) -> List[Dict]:
        cursor = self.collection.find({
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"content": {"$regex": query, "$options": "i"}}
            ]
        })
        articles = []
        async for article in cursor:
            article["_id"] = str(article["_id"])
            articles.append(article)
        return articles

    async def url_exists(self, url: str) -> bool:
        return await self.collection.count_documents({"url": url}) > 0