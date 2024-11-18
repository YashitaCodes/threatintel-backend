import os
import csv
import json
import uuid
import random
import re
import time
from typing import TypedDict, Literal, Set
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
import logging
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from colorama import init, Fore, Back, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Initialize colorama
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter for colored log output"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE
    }

    def format(self, record):
        # Color the entire line based on log level
        color = self.COLORS.get(record.levelname, Fore.WHITE)
        
        # Add emoji indicators
        level_emoji = {
            'DEBUG': '🔍',
            'INFO': '✨',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }
        
        # Special coloring for specific message types
        message = record.getMessage()
        if "Saved" in message:
            message = f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}"
        elif "Skipping duplicate" in message:
            message = f"{Fore.YELLOW}↪️ {message}{Style.RESET_ALL}"
        elif "Error" in message:
            message = f"{Fore.RED}❌ {message}{Style.RESET_ALL}"
        elif "Processing" in message:
            message = f"{Fore.CYAN}⚙️ {message}{Style.RESET_ALL}"
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Construct the log line
        log_line = f"{Fore.WHITE}{timestamp}{Style.RESET_ALL} - {level_emoji.get(record.levelname, '•')} {message}"
        
        return log_line

# Configure logging with custom formatter
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler with custom formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())
logger.addHandler(console_handler)

# File handler for keeping a log file
file_handler = logging.FileHandler('scraper.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Configuration
TEST_MODE = True
TEST_SCRAPES = 1000000

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
    sentiment: Literal["Positive", "Neutral", "Negative"]
    sentimentScore: float

class ArticleTracker:
    """Track processed articles to prevent duplicates"""
    def __init__(self):
        self.processed_urls: Set[str] = set()
        self.csv_filename = 'articles.csv'
        self._load_existing_csv()
    
    def _load_existing_csv(self):
        """Load existing URLs from CSV if it exists"""
        if os.path.exists(self.csv_filename):
            logger.info(f"Loading existing articles from {self.csv_filename}")
            with open(self.csv_filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.processed_urls.add(row['sourceUrl'])
            logger.info(f"Found {len(self.processed_urls)} existing articles")

    def is_processed(self, url: str) -> bool:
        return url in self.processed_urls

    def mark_processed(self, url: str):
        self.processed_urls.add(url)

def clean_html(text: str) -> str:
    """Remove HTML tags from text using regex."""
    logger.debug(f"Cleaning HTML from text: {text[:50]}...")
    cleaned = re.sub(r'<[^>]+>', '', text)
    return cleaned

def truncate_text(text: str, length: int = 100) -> str:
    """Create a snippet by truncating text."""
    if len(text) > length:
        logger.debug(f"Truncating text from {len(text)} characters to {length}")
        return text[:length] + '...'
    return text

def extract_domain_without_tld(url: str) -> str:
    """Extract domain name without TLD from URL."""
    logger.debug(f"Extracting domain from URL: {url}")
    match = re.search(r'://(?:www\.)?([\w-]+)\.', url)
    result = match.group(1) if match else url
    logger.debug(f"Extracted domain: {result}")
    return result

def parse_article(card_element, tracker: ArticleTracker) -> Article | None:
    """Parse a single article card and return structured data."""
    try:
        link = card_element.find('a', class_='card')
        source_url = link.get('href', '')
        
        if tracker.is_processed(source_url):
            logger.info(f"Skipping duplicate article: {source_url}")
            return None
        
        logger.info(f"Parsing new article: {source_url}")
        
        title_div = link.find('div', {'class': 'card-title'}).find('div')
        title = title_div.get_text(strip=True)
        logger.debug(f"Extracted title: {title}")
        
        content_span = link.find('span', class_='text-body-secondary')
        content = clean_html(content_span.get_text(strip=True)) if content_span else ''
        logger.debug(f"Extracted content: {content[:50]}...")
        
        category_span = link.find('span', class_='badge')
        category = category_span.get('title', '') if category_span else 'Uncategorized'
        logger.debug(f"Extracted category: {category}")
        
        footer = link.find('div', class_='card-footer')
        date_text = footer.find('span', class_='text-secondary').get_text(strip=True)
        
        # Convert "Fri 15 Nov" to "2024-11-15" format
        try:
            # Parse the date with current year
            parsed_date = datetime.strptime(f"{date_text} 2024", "%a %d %b %Y")
            
            # If the month is January, we've gone too far back
            if parsed_date.month == 1:
                logger.info("Reached January, stopping scraper")
                return None
                
            # Format date as ISO string
            date = parsed_date.strftime("%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Error parsing date {date_text}: {str(e)}")
            date = None
            
        source = footer.find('span', class_='text-primary').get_text(strip=True)
        
        # Don't create article if date parsing failed
        if not date:
            return None
            
        article = Article(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            snippet=truncate_text(content),
            source=source,
            category=category,
            date=date,
            author=extract_domain_without_tld(source),
            sourceUrl=source_url,
            sentiment="Neutral",
            sentimentScore=random.uniform(0.0, 1.0)
        )
        
        tracker.mark_processed(source_url)
        logger.info(f"Successfully parsed article: {title}")
        return article
    
    except Exception as e:
        logger.error(f"Error parsing article: {str(e)}")
        return None

def save_article_to_csv(article: Article, is_first: bool = False):
    """Save a single article to CSV file."""
    mode = 'w' if is_first else 'a'
    try:
        with open('articles.csv', mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=article.keys())
            if is_first:
                writer.writeheader()
            writer.writerow(article)
        logger.info(f"Saved article to CSV: {article['title']}")
    except Exception as e:
        logger.error(f"Error saving to CSV: {str(e)}")

class MongoDBHandler:
    def __init__(self):
        load_dotenv()
        self.mongo_url = os.getenv('MONGODB_URL')
        if not self.mongo_url:
            raise ValueError("MongoDB URL not found in environment variables")
        
        self.client = MongoClient(self.mongo_url)
        self.db = self.client.talkback
        self.collection = self.db.articles
        logger.info("MongoDB connection initialized successfully")
        
        # Create unique index on sourceUrl
        self.collection.create_index("sourceUrl", unique=True)
        
    def save_article(self, article: Article):
        """Save a single article to MongoDB with upsert."""
        try:
            result = self.collection.update_one(
                {"sourceUrl": article["sourceUrl"]},
                {"$set": article},
                upsert=True
            )
            if result.upserted_id:
                logger.info(f"Inserted new article to MongoDB: {article['title']}")
            else:
                logger.info(f"Updated existing article in MongoDB: {article['title']}")
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {str(e)}")


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
    sentiment: Literal["Positive", "Neutral", "Negative"]
    sentimentScore: float

class WebDriver:
    """Manage Selenium WebDriver instance"""
    def __init__(self):
        logger.info("Initializing Chrome WebDriver")
        options = webdriver.ChromeOptions()
        
        # Remove headless mode
        # options.add_argument('--headless')
        
        # Add common headers and settings to appear more human-like
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        
        # Add additional headers
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        
        # Execute CDP commands to prevent detection
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 10)
        logger.info(f"{Fore.GREEN}WebDriver initialized successfully")

    def __enter__(self):
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("Closing WebDriver")
        self.driver.quit()

class ArticleTracker:
    """Track processed articles to prevent duplicates"""
    def __init__(self):
        self.processed_urls: Set[str] = set()
        self.csv_filename = 'articles.csv'
        self._load_existing_csv()
    
    def _load_existing_csv(self):
        if os.path.exists(self.csv_filename):
            logger.info(f"Loading existing articles from {self.csv_filename}")
            with open(self.csv_filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.processed_urls.add(row['sourceUrl'])
            logger.info(f"Found {len(self.processed_urls)} existing articles")

    def is_processed(self, url: str) -> bool:
        return url in self.processed_urls

    def mark_processed(self, url: str):
        self.processed_urls.add(url)

def scrape_talkback():
    """Main scraping function."""
    logger.info(f"{Fore.CYAN}{'='*50}")
    logger.info(f"{Fore.CYAN}Starting talkback.sh scraper")
    logger.info(f"{Fore.CYAN}{'='*50}")
    
    tracker = ArticleTracker()
    mongo_handler = None if TEST_MODE else MongoDBHandler()
    
    # Add random delays between actions
    def random_delay():
        time.sleep(random.uniform(2, 5))
    
    try:
        with WebDriver() as driver:
            url = 'https://talkback.sh/'
            logger.info(f"Loading {url}")
            driver.get(url)
            # random_delay()  # Add delay after page load
            
            articles_processed = 0
            max_pages = 1000000  # Limit number of pages to prevent infinite loops
            page = 1

            while page <= max_pages:
                # Add random scrolling behavior
                driver.execute_script(f"window.scrollTo(0, {random.randint(300, 700)});")
                # random_delay()
                
                # Process current page articles
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                cards = soup.find_all('div', class_='col')
                
                logger.info(f"Found {len(cards)} articles on page {page}")
                
                # Process articles on current page
                for index, card in enumerate(cards, 1):
                    if TEST_MODE and articles_processed >= TEST_SCRAPES:
                        return
                    
                    article = parse_article(card, tracker)
                    if article:
                        if TEST_MODE:
                            save_article_to_csv(article, is_first=(articles_processed == 0))
                        else:
                            mongo_handler.save_article(article)
                        articles_processed += 1
                
                # Add delay before clicking load more
                # random_delay()
                
                # Try to load more articles
                try:
                    load_more = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-link[hx-get*='page=']:first-of-type"))
                    )
                    old_height = driver.execute_script("return document.body.scrollHeight")
                    driver.execute_script("arguments[0].click();", load_more)
                    logger.info(f"{Fore.CYAN}Clicked 'Load more' button - Page {page}")
                    
                    # Wait for new content to load
                    time.sleep(2)
                    
                    # Verify new content loaded
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height <= old_height:
                        logger.info("No new content loaded, ending pagination")
                        break
                    
                    page += 1
                except TimeoutException:
                    logger.info("No more 'Load more' buttons found")
                    break
                except Exception as e:
                    logger.error(f"Error loading more articles: {str(e)}")
                    break
            
            logger.info(f"{Fore.GREEN}{'='*50}")
            logger.info(f"{Fore.GREEN}Scraping completed successfully")
            logger.info(f"{Fore.GREEN}Total articles processed: {articles_processed}")
            logger.info(f"{Fore.GREEN}{'='*50}")
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        if not TEST_MODE and mongo_handler:
            mongo_handler.client.close()
            logger.info("MongoDB connection closed")

if __name__ == "__main__":
    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"{Fore.CYAN}Talkback.sh Scraper v1.0")
    print(f"{Fore.CYAN}{'='*50}\n")
    scrape_talkback()