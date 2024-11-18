from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import PyMongoError, OperationFailure
from dotenv import load_dotenv
import os
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import logging
from fastapi.encoders import jsonable_encoder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="Security News API",
    description="API for retrieving security news articles",
    version="1.0.0"
)

origins = [
    "http://localhost:3000",     
    "http://localhost:8000",         
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "https://threatintel.yashita.live"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection with error handling
try:
    mongo_url = os.getenv('MONGODB_URL')
    if not mongo_url:
        raise ValueError("MONGODB_URL not found in .env file")
    
    client = MongoClient(mongo_url)
    # Test the connection
    client.admin.command('ping')
    db = client['security_news']
    collection = db['articles']
    logger.info("Successfully connected to MongoDB")
except PyMongoError as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error while connecting to MongoDB: {e}")
    raise

class Article(BaseModel):
    id: str = Field(..., description="Unique identifier for the article")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Full article content")
    snippet: str = Field(..., description="Article snippet or summary")
    source: str = Field(..., description="Source of the article")
    category: str = Field(..., description="Article category")
    date: datetime = Field(..., description="Publication date")
    author: str = Field(..., description="Article author")
    sourceUrl: str = Field(..., description="Original article URL")
    sentiment: str = Field(..., description="Sentiment analysis result")
    sentimentScore: float = Field(..., description="Sentiment score")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "article123",
                "title": "New Ransomware Attack Discovered",
                "content": "Article content here...",
                "snippet": "Brief summary of the article...",
                "source": "SecurityWeek",
                "category": "malware",
                "date": "2024-03-14T12:00:00Z",
                "author": "John Doe",
                "sourceUrl": "https://example.com/article",
                "sentiment": "negative",
                "sentimentScore": -0.75
            }
        }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"}
    )

@app.get("/", response_description="Welcome message")
async def root():
    """Root endpoint returning API information"""
    return {
        "message": "Welcome to the Security News API",
        "version": "1.0.0",
        "documentation": "/docs",
        "status": "operational"
    }

@app.get("/articles", response_model=List[Article])
async def get_all_articles(
    skip: int = Query(0, ge=0, description="Number of articles to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of articles to return"),
    sort_by: str = Query("date", description="Field to sort by"),
    order: str = Query("desc", description="Sort order (asc or desc)")
):
    """Get all articles with pagination and sorting"""
    try:
        sort_direction = -1 if order.lower() == "desc" else 1
        articles = list(collection.find({})
                       .sort(sort_by, sort_direction)
                       .skip(skip)
                       .limit(limit))
        
        if not articles:
            raise HTTPException(status_code=404, detail="No articles found")
        
        for article in articles:
            article['_id'] = str(article['_id'])
            
        return articles
    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        raise HTTPException(status_code=500, detail="Error fetching articles")

@app.get("/articles/{article_id}", response_model=Article)
async def get_article_by_id(article_id: str):
    """Get a specific article by its ID"""
    try:
        article = collection.find_one({"id": article_id})
        if not article:
            raise HTTPException(status_code=404, 
                              detail=f"Article {article_id} not found")
        article['_id'] = str(article['_id'])
        return article
    except Exception as e:
        logger.error(f"Error fetching article {article_id}: {e}")
        raise HTTPException(status_code=500, 
                          detail=f"Error fetching article {article_id}")

@app.get("/articles/search", response_model=List[Article])
async def search_articles(
    query: str = Query(..., min_length=1, description="Search query"),
    field: str = Query("title", description="Field to search in"),
    skip: int = Query(0, ge=0, description="Number of articles to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of articles to return")
):
    """Search articles by title, content, or snippet"""
    valid_fields = ["title", "content", "snippet"]
    if field not in valid_fields:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid search field. Must be one of: {', '.join(valid_fields)}"
        )
    
    try:
        articles = list(collection.find(
            {field: {"$regex": query, "$options": "i"}}
        ).skip(skip).limit(limit))
        
        if not articles:
            raise HTTPException(
                status_code=404, 
                detail="No articles found matching the search criteria"
            )
        
        for article in articles:
            article['_id'] = str(article['_id'])
            
        return articles
    except Exception as e:
        logger.error(f"Error searching articles: {e}")
        raise HTTPException(status_code=500, detail="Error searching articles")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        client.admin.command('ping')
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
        )

@app.on_event("startup")
async def startup_event():
    """Startup events"""
    logger.info("API starting up...")
    # Add any startup tasks here

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown events"""
    logger.info("API shutting down...")
    client.close()