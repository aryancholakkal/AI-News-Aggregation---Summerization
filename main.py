from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
import feedparser
import json
import os
import time
import csv
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional
import threading
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
app = FastAPI(title="RSS Feed Summarizer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
max_text_length = 7000
feeds_file = "rss_feeds.json"
csv_file = "news_summaries.csv"
json_file = "news_summaries.json"

load_dotenv()
# Default settings
default = {
    'url': os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"),
    'api_key':os.environ.get("OPENAI_API_KEY",""),
    'model': os.environ.get("FEEDSUMMARIZER_MODEL", "gpt-3.5-turbo"),
    'system': os.environ.get("FEEDSUMMARIZER_SYSTEM", "You are an expert summarizer."),
    'instruction': os.environ.get("FEEDSUMMARIZER_INSTRUCTION", "Summarize this article into a short, punchy tech fact (max 2 sentences) to put in a newsletter."),
    'maximum': int(os.environ.get("FEEDSUMMARIZER_MAX_ARTICLES", "10")),
    'dyk_prompt': os.environ.get("FEEDSUMMARIZER_DYK_INSTRUCTION","Convert the following article into a single-sentence 'Did you know...' style fact. Be fun, factual, and concise."),
    'time_lapse': int(os.environ.get("FEEDSUMMARIZER_TIME_LAPSE", "86400"))
}

print("HII",os.environ.get("OPENAI_API_KEY"))

# Pydantic models
class FeedRequest(BaseModel):
    url: str
    name: Optional[str] = ""

class FeedResponse(BaseModel):
    id: int
    name: str
    url: str

class ArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    date: str
    author: str
    timestamp: str
    summary: str
    feed_name: Optional[str] = ""

class ArticleURLRequest(BaseModel):
    url: str

class NewsArticle:
    def __init__(self, entry, max_text_length):
        self.title = getattr(entry, 'title', 'Unknown')
        self.url = getattr(entry, 'link', 'NO LINK')
        self.date = getattr(entry, 'updated', getattr(entry, 'published', 'Unknown'))
        self.author = getattr(entry, 'author', 'Unknown')
        self.timestamp = datetime.now().isoformat()
        self.text = self.get_page_content(self.url, max_text_length)
        self.summary = ""
        self.feed_name = ""
        
    def get_page_content(self, url, max_text_length):
        if url == "NO LINK":
            return "The feed entry doesn't seem to have any URL."
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except Exception as e:
            return f"The page {url} could not be loaded: {str(e)}"
        
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all("p")
        
        if paragraphs:
            text = "\n".join(p.get_text() for p in paragraphs)
            words = text.split()
            if len(words) > max_text_length:
                text = " ".join(words[:max_text_length]) + "..."
            return f"Content of {url}:\n{text}"
        else:
            return f"The web page at {url} doesn't seem to have any readable content."
    
    def summarize(self, settings):
        if self.text and "doesn't seem to have any URL" not in self.text:
            self.summary = generate_ai_response(self.text, settings)
        else:
            self.summary = "Could not summarize - no content available"
        return self.summary
    
    def to_dict(self):
        return {
            'title': self.title,
            'url': self.url,
            'date': self.date,
            'author': self.author,
            'timestamp': self.timestamp,
            'summary': self.summary,
            'feed_name': getattr(self, 'feed_name', '')
        }

def generate_ai_response(content, settings):
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings['api_key']}"
        }
        
        messages = [
            {"role": "system", "content": settings['system']},
            {"role": "user", "content": f"{content}\n\n{settings['instruction']}"}
        ]
        
        data = {
            'model': settings['model'],
            'messages': messages,
            'max_tokens': 500,
            'temperature': 0.7
        }
        
        response = requests.post(
            f"{settings['url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"Error generating summary: {response.status_code}"
            
    except Exception as e:
        return f"Error generating response: {str(e)}"

def fetch_article_text(url: str, max_text_length: int = 7000) -> str:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return f"The page {url} could not be loaded: {str(e)}"

    soup = BeautifulSoup(response.content, "html.parser")
    paragraphs = soup.find_all("p")

    if paragraphs:
        text = "\n".join(p.get_text() for p in paragraphs)
        words = text.split()
        if len(words) > max_text_length:
            text = " ".join(words[:max_text_length]) + "..."
        return f"Content of {url}:\n{text}"
    else:
        return f"The web page at {url} doesn't seem to have any readable content."


def load_feeds():
    """Load RSS feeds from JSON file"""
    if os.path.exists(feeds_file):
        try:
            with open(feeds_file, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_feeds(feeds):
    """Save RSS feeds to JSON file"""
    with open(feeds_file, 'w') as f:
        json.dump(feeds, f, indent=2)

def save_to_csv(articles):
    """Save articles to CSV file"""
    fieldnames = ['title', 'url', 'date', 'author', 'timestamp', 'summary', 'feed_name']
    
    file_exists = os.path.exists(csv_file)
    
    with open(csv_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for article in articles:
            writer.writerow(article.to_dict())

def save_to_json(articles):
    """Save articles to JSON file"""
    existing_data = []
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except:
            existing_data = []
    
    for article in articles:
        existing_data.append(article.to_dict())
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

def process_feeds_background():
    """Background process to handle RSS feeds - runs weekly"""
    print("Starting weekly RSS feed processing...")
    feeds = load_feeds()
    if not feeds:
        print("No feeds found to process")
        return
    
    settings = default.copy()
    all_articles = []
    
    for feed_info in feeds:
        try:
            print(f"Processing feed: {feed_info['name']}")
            feed = feedparser.parse(feed_info['url'])
            feed_title = getattr(feed.feed, 'title', feed_info['name'])
            
            articles = []
            now = time.time()
            
            for entry in feed.entries[:settings['maximum']]:
                if hasattr(entry, 'updated_parsed'):
                    then = time.mktime(entry.updated_parsed)
                elif hasattr(entry, 'published_parsed'):
                    then = time.mktime(entry.published_parsed)
                else:
                    then = now
                
                if (now - then) < settings['time_lapse']:
                    article = NewsArticle(entry, max_text_length)
                    article.feed_name = feed_title
                    articles.append(article)
            
            print(f"Found {len(articles)} recent articles from {feed_title}")
            
            for article in articles:
                article.summarize(settings)
                all_articles.append(article)
            
        except Exception as e:
            print(f"Error processing {feed_info['name']}: {str(e)}")
    
    if all_articles:
        save_to_csv(all_articles)
        save_to_json(all_articles)
        print(f"Processed and saved {len(all_articles)} articles")
    else:
        print("No new articles to process")

# FastAPI Endpoints

@app.get("/", response_class=HTMLResponse)
async def get_home():
    """Serve the main HTML page"""
    return HTMLResponse(content=get_html_content())

@app.get("/api/articles", response_model=List[ArticleResponse])
async def get_articles(limit: int = 10):
    """Get recent articles"""
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            articles.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            result = []
            for i, article in enumerate(articles[:limit], 1):
                result.append(ArticleResponse(
                    id=i,
                    title=article['title'],
                    url=article['url'],
                    date=article['date'],
                    author=article['author'],
                    timestamp=article['timestamp'],
                    summary=article['summary'],
                    feed_name=article.get('feed_name', '')
                ))
            
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error loading articles: {str(e)}")
    else:
        return []

@app.get("/api/article/{article_id}/summary")
async def get_article_summary(article_id: int):
    """Get summary for a specific article"""
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            articles.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            if 1 <= article_id <= len(articles):
                article = articles[article_id - 1]
                return {"summary": article['summary']}
            else:
                raise HTTPException(status_code=404, detail="Article not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error loading article: {str(e)}")
    else:
        raise HTTPException(status_code=404, detail="No articles available")

@app.get("/api/feeds", response_model=List[FeedResponse])
async def get_feeds():
    """Get all RSS feeds"""
    feeds = load_feeds()
    result = []
    for i, feed in enumerate(feeds, 1):
        result.append(FeedResponse(
            id=i,
            name=feed['name'],
            url=feed['url']
        ))
    return result

@app.post("/api/feeds")
async def add_feed(feed_request: FeedRequest):
    """Add a new RSS feed"""
    feeds = load_feeds()
    
    name = feed_request.name if feed_request.name else feed_request.url
    
    # Check if feed already exists
    for feed in feeds:
        if feed['url'] == feed_request.url:
            raise HTTPException(status_code=400, detail="Feed already exists")
    
    # Validate feed
    try:
        parsed_feed = feedparser.parse(feed_request.url)
        if parsed_feed.bozo:
            raise HTTPException(status_code=400, detail="Invalid RSS feed")
    except:
        raise HTTPException(status_code=400, detail="Cannot parse RSS feed")
    
    feeds.append({'url': feed_request.url, 'name': name})
    save_feeds(feeds)
    return {"message": f"Feed '{name}' added successfully"}

@app.delete("/api/feeds/{feed_id}")
async def remove_feed(feed_id: int):
    """Remove an RSS feed"""
    feeds = load_feeds()
    
    if 1 <= feed_id <= len(feeds):
        removed_feed = feeds.pop(feed_id - 1)
        save_feeds(feeds)
        return {"message": f"Feed '{removed_feed['name']}' removed successfully"}
    else:
        raise HTTPException(status_code=404, detail="Feed not found")

@app.post("/api/process-feeds")
async def manual_process_feeds(background_tasks: BackgroundTasks):
    """Manually trigger feed processing"""
    background_tasks.add_task(process_feeds_background)
    return {"message": "Feed processing started"}

@app.post("/api/convert-url")
async def convert_url_to_did_you_know(request: ArticleURLRequest):
    print("hi",request.url)
    article_text = fetch_article_text(request.url, max_text_length)

    if "could not be loaded" in article_text or "doesn't seem to have" in article_text:
        raise HTTPException(status_code=400, detail="Failed to extract readable content from the URL.")

    # Build instruction prompt
    settings = default.copy()
    prompt = f"{article_text}\n\n{settings['dyk_prompt']}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {default['api_key']}"
    }

    messages = [
        {"role": "system", "content": default['system']},
        {"role": "user", "content": prompt}
    ]

    data = {
        "model": default["model"],
        "messages": messages,
        "max_tokens": 200,
        "temperature": 0.7,
    }

    try:
        response = requests.post(
            f"{default['url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"].strip()
            return {"did_you_know": result}
        else:
            raise HTTPException(status_code=500, detail="Failed to generate summary from LLM.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during LLM call: {str(e)}")


def get_html_content():
    """Generate the HTML content for the UI"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RSS Feed Summarizer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 2px solid #eee;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            margin-right: 5px;
            border-radius: 5px 5px 0 0;
        }
        .tab.active {
            background-color: #007bff;
            color: white;
        }
        .tab-content {
            display: none;
            padding: 20px 0;
        }
        .tab-content.active {
            display: block;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 2px;
        }
        button:hover {
            background-color: #0056b3;
        }
        button.danger {
            background-color: #dc3545;
        }
        button.danger:hover {
            background-color: #c82333;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .form-group input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .add-feed-form {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.4);
        }
        .modal-content {
            background-color: white;
            margin: 15% auto;
            padding: 20px;
            border-radius: 8px;
            width: 80%;
            max-width: 600px;
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover {
            color: black;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .two-column {
            display: flex;
            gap: 20px;
        }
        .column {
            flex: 1;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>RSS Feed Summarizer</h1>
        
        <div class="tabs">
            <div class="tab active" onclick="openTab(event, 'results')">View Results</div>
            <div class="tab" onclick="openTab(event, 'feeds')">Manage Feeds</div>
        </div>
        
        <!-- View Results Tab -->
        <div id="results" class="tab-content active">
            <h2>Recent Articles</h2>
            <div id="articles-loading" class="loading">Loading articles...</div>
            <table id="articles-table" style="display: none;">
                <thead>
                    <tr>
                        <th>Sl. No</th>
                        <th>Title</th>
                        <th>Summary</th>
                        <th>Original URL</th>
                    </tr>
                </thead>
                <tbody id="articles-tbody">
                </tbody>
            </table>
        </div>
        
        <!-- Manage Feeds Tab -->
        <div id="feeds" class="tab-content">
            <h2>Manage RSS Feeds</h2>
            <div class="two-column">
                <div class="column">
                    <h3>Current Feeds</h3>
                    <div id="feeds-loading" class="loading">Loading feeds...</div>
                    <table id="feeds-table" style="display: none;">
                        <thead>
                            <tr>
                                <th>Sl. No</th>
                                <th>Name</th>
                                <th>URL</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody id="feeds-tbody">
                        </tbody>
                    </table>
                </div>
                
                <div class="column">
                    <div class="add-feed-form">
                        <h3>Add New Feed</h3>
                        <div class="form-group">
                            <label for="feed-url">RSS Feed URL:</label>
                            <input type="url" id="feed-url" placeholder="https://example.com/rss">
                        </div>
                        <div class="form-group">
                            <label for="feed-name">Feed Name (optional):</label>
                            <input type="text" id="feed-name" placeholder="My News Source">
                        </div>
                        <button onclick="addFeed()">Add Feed</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Summary Modal -->
    <div id="summary-modal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeSummaryModal()">&times;</span>
            <h2>Article Summary</h2>
            <div id="summary-content"></div>
        </div>
    </div>
    
    <script>
        let articlesData = [];
        let feedsData = [];
        
        // Tab functionality
        function openTab(evt, tabName) {
            var i, tabcontent, tabs;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            tabs = document.getElementsByClassName("tab");
            for (i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove("active");
            }
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
            
            // Load data when tab is opened
            if (tabName === 'results') {
                loadArticles();
            } else if (tabName === 'feeds') {
                loadFeeds();
            }
        }
        
        // Load articles
        async function loadArticles() {
            document.getElementById('articles-loading').style.display = 'block';
            document.getElementById('articles-table').style.display = 'none';
            
            try {
                const response = await fetch('/api/articles?limit=20');
                articlesData = await response.json();
                displayArticles();
            } catch (error) {
                console.error('Error loading articles:', error);
                document.getElementById('articles-loading').innerHTML = 'Error loading articles';
            }
        }
        
        // Display articles in table
        function displayArticles() {
            const tbody = document.getElementById('articles-tbody');
            tbody.innerHTML = '';
            
            articlesData.forEach((article, index) => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${article.id}</td>
                    <td>${article.title}</td>
                    <td><button onclick="showSummary(${article.id})">View Summary</button></td>
                    <td><button onclick="openOriginalUrl('${article.url}')">Open URL</button></td>
                `;
                tbody.appendChild(row);
            });
            
            document.getElementById('articles-loading').style.display = 'none';
            document.getElementById('articles-table').style.display = 'table';
        }
        
        // Show summary modal
        async function showSummary(articleId) {
            try {
                const response = await fetch(`/api/article/${articleId}/summary`);
                const data = await response.json();
                document.getElementById('summary-content').innerHTML = `<p>${data.summary}</p>`;
                document.getElementById('summary-modal').style.display = 'block';
            } catch (error) {
                console.error('Error loading summary:', error);
                alert('Error loading summary');
            }
        }
        
        // Close summary modal
        function closeSummaryModal() {
            document.getElementById('summary-modal').style.display = 'none';
        }
        
        // Open original URL
        function openOriginalUrl(url) {
            window.open(url, '_blank');
        }
        
        // Load feeds
        async function loadFeeds() {
            document.getElementById('feeds-loading').style.display = 'block';
            document.getElementById('feeds-table').style.display = 'none';
            
            try {
                const response = await fetch('/api/feeds');
                feedsData = await response.json();
                displayFeeds();
            } catch (error) {
                console.error('Error loading feeds:', error);
                document.getElementById('feeds-loading').innerHTML = 'Error loading feeds';
            }
        }
        
        // Display feeds in table
        function displayFeeds() {
            const tbody = document.getElementById('feeds-tbody');
            tbody.innerHTML = '';
            
            feedsData.forEach((feed, index) => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${feed.id}</td>
                    <td>${feed.name}</td>
                    <td><a href="${feed.url}" target="_blank">${feed.url}</a></td>
                    <td><button class="danger" onclick="removeFeed(${feed.id})">Remove</button></td>
                `;
                tbody.appendChild(row);
            });
            
            document.getElementById('feeds-loading').style.display = 'none';
            document.getElementById('feeds-table').style.display = 'table';
        }
        
        // Add feed
        async function addFeed() {
            const url = document.getElementById('feed-url').value;
            const name = document.getElementById('feed-name').value;
            
            if (!url) {
                alert('Please enter a feed URL');
                return;
            }
            
            try {
                const response = await fetch('/api/feeds', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        url: url,
                        name: name
                    }),
                });
                
                if (response.ok) {
                    const data = await response.json();
                    alert(data.message);
                    document.getElementById('feed-url').value = '';
                    document.getElementById('feed-name').value = '';
                    loadFeeds();
                } else {
                    const error = await response.json();
                    alert('Error: ' + error.detail);
                }
            } catch (error) {
                console.error('Error adding feed:', error);
                alert('Error adding feed');
            }
        }
        
        // Remove feed
        async function removeFeed(feedId) {
            if (!confirm('Are you sure you want to remove this feed?')) {
                return;
            }
            
            try {
                const response = await fetch(`/api/feeds/${feedId}`, {
                    method: 'DELETE',
                });
                
                if (response.ok) {
                    const data = await response.json();
                    alert(data.message);
                    loadFeeds();
                } else {
                    const error = await response.json();
                    alert('Error: ' + error.detail);
                }
            } catch (error) {
                console.error('Error removing feed:', error);
                alert('Error removing feed');
            }
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('summary-modal');
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        }
        
        // Initialize the page
        document.addEventListener('DOMContentLoaded', function() {
            loadArticles();
        });
    </script>
</body>
</html>
    """

# Initialize scheduler for weekly processing
scheduler = BackgroundScheduler()

@app.on_event("startup")
async def startup_event():
    # Create initial feeds file with sample feed if it doesn't exist
    if not os.path.exists(feeds_file):
        sample_feeds = [
            {"url": "https://news.ycombinator.com/rss", "name": "Hacker News"},
            {"url": "https://feeds.bbci.co.uk/news/rss.xml", "name": "BBC News"}
        ]
        save_feeds(sample_feeds)
    
    # Schedule weekly processing (every Monday at 9:00 AM)
    scheduler.add_job(
        process_feeds_background,
        CronTrigger(day_of_week=0, hour=9, minute=0),  # 0 = Monday
        id='weekly_feed_processing'
    )
    scheduler.start()
    print("RSS Feed Summarizer started with weekly processing enabled")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

if __name__ == "__main__":
    print("Starting RSS Feed Summarizer Backend...")
    print("FastAPI will run on http://localhost:8000")
    print("Automatic weekly processing is enabled (Mondays at 9:00 AM)")
    process_feeds_background()
    print("Commencing automatic processing")
    uvicorn.run(app, host="0.0.0.0", port=8000)