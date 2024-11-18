import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime
import sys

# Load environment variables
load_dotenv()

def connect_to_mongodb():
    """Connect to MongoDB using URL from .env file"""
    mongo_url = os.getenv('MONGODB_URL')
    if not mongo_url:
        raise ValueError("MONGODB_URL not found in .env file")
    
    try:
        client = MongoClient(mongo_url)
        # Test connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        sys.exit(1)

def process_date(date_str):
    """Convert date string to datetime object"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except:
        return datetime.now()  # fallback to current date

def read_csv_file(file_path):
    """Read and validate CSV file"""
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found at {file_path}")
        
        print(f"📂 Attempting to read CSV from: {file_path}")
        df = pd.read_csv(file_path)
        
        # Add debug information about the file
        print(f"📄 File size: {os.path.getsize(file_path)} bytes")
        
        if df.empty:
            print("⚠️ DataFrame is empty. File might be empty or corrupted.")
            print(f"🔍 File content preview:")
            with open(file_path, 'r') as f:
                print(f.read(500))  # Print first 500 characters
            raise ValueError("CSV file is empty")
            
        print(f"📊 Successfully loaded {len(df)} rows from CSV")
        return df
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        sys.exit(1)

def main():
    # File path - try multiple possible locations
    possible_paths = [
        'data/articles.csv',
        './data/articles.csv',
        '../data/articles.csv',
        'app/data/articles.csv',
        'articles.csv'

    ]
    
    csv_path = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    if not csv_path:
        print("❌ Could not find articles.csv in any of the expected locations")
        sys.exit(1)
    
    # Read CSV file
    df = read_csv_file(csv_path)
    
    # Connect to MongoDB
    client = connect_to_mongodb()
    db = client['security_news']
    collection = db['articles']
    
    # Convert DataFrame to list of dictionaries
    articles = df.to_dict('records')
    
    if not articles:
        print("❌ No articles found in CSV")
        sys.exit(1)
    
    # Process each article
    processed_articles = []
    for article in articles:
        # Clean and validate each article
        cleaned_article = {
            'id': str(article.get('id', '')),
            'title': str(article.get('title', '')),
            'content': str(article.get('content', '')),
            'snippet': str(article.get('snippet', '')),
            'source': str(article.get('source', '')),
            'category': str(article.get('category', '')),
            'date': process_date(article.get('date')),
            'author': str(article.get('author', '')),
            'sourceUrl': str(article.get('sourceUrl', '')),
            'sentiment': str(article.get('sentiment', 'Neutral')),
            'sentimentScore': float(article.get('sentimentScore', 0.0))
        }
        processed_articles.append(cleaned_article)
    
    try:
        # First, remove any existing articles to avoid duplicates
        collection.delete_many({})
        print(f"🧹 Cleared existing articles from database")
        
        # Insert new articles
        if processed_articles:
            result = collection.insert_many(processed_articles)
            print(f"✅ Successfully inserted {len(result.inserted_ids)} articles")
        else:
            raise ValueError("No valid articles to insert")
            
    except Exception as e:
        print(f"❌ Error inserting articles: {e}")
        
    finally:
        print("👋 Closing MongoDB connection")
        client.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)