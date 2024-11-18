import aiohttp
import asyncio
import json
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Optional
from ..database.base import DatabaseHandler

logging.basicConfig(
    filename='logs/scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class NewsScraper:
    def __init__(self, config_path: str, db_handler: DatabaseHandler):
        self.config = self._load_config(config_path)
        self.db_handler = db_handler

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return json.load(f)

    async def scrape_website(self, site_name: str, site_config: Dict):
        async with aiohttp.ClientSession() as session:
            try:
                base_url = site_config['base_url']
                selectors = site_config['selectors']
                
                # Get article list page
                async with session.get(base_url) as response:
                    if response.status != 200:
                        logging.error(f"Failed to fetch {base_url}: {response.status}")
                        return
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    article_list = soup.select(selectors['article_list'])
                    
                    for article_element in article_list:
                        try:
                            link_element = article_element.select_one(selectors['article_link'])
                            if not link_element:
                                continue

                            article_url = link_element.get('href')
                            if not article_url:
                                continue

                            # Check if article already exists
                            if await self.db_handler.url_exists(article_url):
                                continue

                            # Scrape individual article
                            article_data = await self._scrape_article(
                                session, article_url, selectors, site_name, site_config
                            )
                            
                            if article_data:
                                await self.db_handler.save_article(article_data)
                                logging.info(f"Saved article: {article_data['title']}")

                        except Exception as e:
                            logging.error(f"Error scraping article: {str(e)}")
                            continue

            except Exception as e:
                logging.error(f"Error scraping website {site_name}: {str(e)}")

    async def _scrape_article(self, session: aiohttp.ClientSession, url: str, 
                            selectors: Dict, site_name: str, site_config: Dict) -> Optional[Dict]:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                title = soup.select_one(selectors['title'])
                content = soup.select_one(selectors['content'])
                date = soup.select_one(selectors['date'])
                author = soup.select_one(selectors.get('author'))
                category = soup.select_one(selectors.get('category'))
                
                if not all([title, content]):
                    return None

                return {
                    'title': title.text.strip(),
                    'content': content.text.strip(),
                    'url': url,
                    'published_date': date.text.strip() if date else datetime.now().isoformat(),
                    'source_website': site_name,
                    'author': author.text.strip() if author else site_config.get('default_author', 'Unknown'),
                    'category': category.text.strip() if category else site_config.get('default_category', 'General')
                }

        except Exception as e:
            logging.error(f"Error scraping article {url}: {str(e)}")
            return None

    async def run_scraper(self):
        for site_name, site_config in self.config.items():
            await self.scrape_website(site_name, site_config)

