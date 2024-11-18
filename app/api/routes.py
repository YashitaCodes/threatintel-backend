from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..database.base import DatabaseHandler

router = APIRouter()

def init_routes(db_handler: DatabaseHandler) -> APIRouter:
    
    @router.get("/articles")
    async def list_articles(
        skip: int = Query(default=0, ge=0),
        limit: int = Query(default=10, ge=1, le=100)
    ):
        articles = await db_handler.get_articles(skip=skip, limit=limit)
        return {"articles": articles, "skip": skip, "limit": limit}

    @router.get("/articles/{article_id}")
    async def get_article(article_id: str):
        article = await db_handler.get_article(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        return article

    @router.get("/articles/search")
    async def search_articles(q: str = Query(..., min_length=1)):
        articles = await db_handler.search_articles(q)
        return {"articles": articles, "query": q}

    return router

