import json
import asyncio
import logging
from fastapi import FastAPI
from app.scrapers.news_scraper import NewsScraper
from app.api.routes import init_routes
from app.database.mongodb_handler import MongoDBHandler
from app.database.csv_handler import CSVHandler

# Load configuration
with open('config/app_config.json', 'r') as f:
    app_config = json.load(f)

# Initialize database handler based on environment
if app_config['environment'] == 'development':
    db_handler = CSVHandler(app_config['csv_path'])
else:
    db_handler = MongoDBHandler(
        app_config['mongodb_uri'],
        app_config['database_name']
    )

# Initialize FastAPI app
app = FastAPI(
    title="News Scraper API",
    description="API for accessing scraped news articles",
    version="1.0.0"
)

# Initialize routes
app.include_router(init_routes(db_handler), prefix="/api/v1")

# Initialize scraper
scraper = NewsScraper('config/scraper_config.json', db_handler)

# Schedule scraping task
async def schedule_scraping():
    while True:
        try:
            await scraper.run_scraper()
            await asyncio.sleep(app_config['scraping_interval_minutes'] * 60)
        except Exception as e:
            logging.error(f"Error in scheduled scraping: {str(e)}")
            await asyncio.sleep(60)  # Wait a minute before retrying

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(schedule_scraping())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)