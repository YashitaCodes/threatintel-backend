from abc import ABC, abstractmethod
from typing import List, Optional, Dict, TypedDict

class Article(TypedDict):
    id: str
    title: str
    content: str
    snippet: str
    source: str
    category: str
    date: str
    author: str
    sourceUrl: str
    sentiment: str
    sentimentScore: float
    url: str

class DatabaseHandler(ABC):
    @abstractmethod
    async def save_article(self, article: Dict) -> str:
        pass

    @abstractmethod
    async def get_article(self, article_id: str) -> Optional[Article]:
        pass

    @abstractmethod
    async def get_articles(self, skip: int = 0, limit: int = 10) -> List[Article]:
        pass

    @abstractmethod
    async def search_articles(self, query: str) -> List[Article]:
        pass

    @abstractmethod
    async def url_exists(self, url: str) -> bool:
        pass