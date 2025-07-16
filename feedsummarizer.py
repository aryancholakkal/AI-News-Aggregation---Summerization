import requests
import feedparser
import json
import os
import sys
import time
import csv
import gradio as gr
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
import threading
import queue

# Global variables
max_text_length = 7000
feeds_file = "rss_feeds.json"
csv_file = "news_summaries.csv"
json_file = "news_summaries.json"

# Default settings
default = {
    'url': os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"),
    'api_key': os.environ.get("OPENAI_API_KEY", ""),
    'model': os.environ.get("FEEDSUMMARIZER_MODEL", "gpt-3.5-turbo"),
    'system': os.environ.get("FEEDSUMMARIZER_SYSTEM", "You are an expert summarizer."),
    'instruction': os.environ.get("FEEDSUMMARIZER_INSTRUCTION", "Summarize this article in 2-3 sentences."),
    'maximum': int(os.environ.get("FEEDSUMMARIZER_MAX_ARTICLES", "10")),
    'time_lapse': int(os.environ.get("FEEDSUMMARIZER_TIME_LAPSE", "86400"))
}

class NewsArticle:
    def __init__(self, entry, max_text_length):
        self.title = getattr(entry, 'title', 'Unknown')
        self.url = getattr(entry, 'link', 'NO LINK')
        self.date = getattr(entry, 'updated', getattr(entry, 'published', 'Unknown'))
        self.author = getattr(entry, 'author', 'Unknown')
        self.timestamp = datetime.now().isoformat()
        self.text = self.get_page_content(self.url, max_text_length)
        self.summary = ""
        
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
            'summary': self.summary
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

def add_feed(url, name=""):
    """Add a new RSS feed"""
    feeds = load_feeds()
    
    if not name:
        name = url
    
    # Check if feed already exists
    for feed in feeds:
        if feed['url'] == url:
            return False, f"Feed {url} already exists"
    
    # Validate feed
    try:
        parsed_feed = feedparser.parse(url)
        if parsed_feed.bozo:
            return False, f"Invalid RSS feed: {url}"
    except:
        return False, f"Cannot parse RSS feed: {url}"
    
    feeds.append({'url': url, 'name': name})
    save_feeds(feeds)
    return True, f"Feed '{name}' added successfully"

def remove_feed(url):
    """Remove an RSS feed"""
    feeds = load_feeds()
    original_length = len(feeds)
    feeds = [feed for feed in feeds if feed['url'] != url]
    
    if len(feeds) < original_length:
        save_feeds(feeds)
        return True, f"Feed {url} removed successfully"
    else:
        return False, f"Feed {url} not found"

def get_feeds_display():
    """Get feeds for display in Gradio"""
    feeds = load_feeds()
    if not feeds:
        return "No RSS feeds configured"
    
    display_text = "Current RSS Feeds:\n"
    for i, feed in enumerate(feeds, 1):
        display_text += f"{i}. {feed['name']} - {feed['url']}\n"
    
    return display_text

def save_to_csv(articles):
    """Save articles to CSV file"""
    fieldnames = ['title', 'url', 'date', 'author', 'timestamp', 'summary']
    
    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(csv_file)
    
    with open(csv_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for article in articles:
            writer.writerow(article.to_dict())

def save_to_json(articles):
    """Save articles to JSON file"""
    # Load existing data if file exists
    existing_data = []
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except:
            existing_data = []
    
    # Add new articles
    for article in articles:
        existing_data.append(article.to_dict())
    
    # Save updated data
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

def process_feeds(progress_callback=None):
    """Process all RSS feeds and generate summaries"""
    feeds = load_feeds()
    if not feeds:
        return "No RSS feeds configured"
    
    settings = default.copy()
    all_articles = []
    results = []
    
    for i, feed_info in enumerate(feeds):
        if progress_callback:
            progress_callback(f"Processing feed {i+1}/{len(feeds)}: {feed_info['name']}")
        
        try:
            feed = feedparser.parse(feed_info['url'])
            feed_title = getattr(feed.feed, 'title', feed_info['name'])
            
            articles = []
            now = time.time()
            
            for entry in feed.entries[:settings['maximum']]:
                # Check if article is recent
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
            
            # Generate summaries
            for j, article in enumerate(articles):
                if progress_callback:
                    progress_callback(f"Summarizing article {j+1}/{len(articles)} from {feed_title}")
                article.summarize(settings)
                all_articles.append(article)
            
            results.append(f"Processed {len(articles)} articles from {feed_title}")
            
        except Exception as e:
            results.append(f"Error processing {feed_info['name']}: {str(e)}")
    
    # Save to files
    if all_articles:
        save_to_csv(all_articles)
        save_to_json(all_articles)
        results.append(f"\nSaved {len(all_articles)} articles to {csv_file} and {json_file}")
    
    return "\n".join(results)

def get_recent_summaries(limit=10):
    """Get recent summaries for display"""
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            # Sort by timestamp (most recent first)
            articles.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            display_text = f"Recent {min(limit, len(articles))} Articles:\n\n"
            for i, article in enumerate(articles[:limit], 1):
                display_text += f"{i}. **{article['title']}**\n"
                display_text += f"   Author: {article['author']}\n"
                display_text += f"   Date: {article['date']}\n"
                display_text += f"   Summary: {article['summary']}\n"
                display_text += f"   URL: {article['url']}\n\n"
            
            return display_text
        except:
            return "Error loading summaries"
    else:
        return "No summaries available. Run 'Process Feeds' first."

# Gradio Interface
def create_gradio_interface():
    with gr.Blocks(title="RSS Feed Summarizer", theme='NoCrypt/miku') as iface:
        gr.Markdown("# RSS Feed Summarizer")
        gr.Markdown("Automatically summarize RSS feeds using AI and save results to CSV and JSON files.")
        
        with gr.Tabs():
            # Feed Management Tab
            with gr.Tab("Manage Feeds"):
                gr.Markdown("### Add RSS Feed")
                with gr.Row():
                    feed_url = gr.Textbox(label="RSS Feed URL", placeholder="https://example.com/rss")
                    feed_name = gr.Textbox(label="Feed Name (optional)", placeholder="My News Source")
                
                add_btn = gr.Button("Add Feed", variant="primary")
                add_result = gr.Textbox(label="Result", interactive=False)
                
                gr.Markdown("### Remove RSS Feed")
                remove_url = gr.Textbox(label="RSS Feed URL to Remove", placeholder="https://example.com/rss")
                remove_btn = gr.Button("Remove Feed", variant="secondary")
                remove_result = gr.Textbox(label="Result", interactive=False)
                
                gr.Markdown("### Current Feeds")
                feeds_display = gr.Textbox(label="RSS Feeds", value=get_feeds_display(), interactive=False, lines=10)
                refresh_btn = gr.Button("Refresh List")
                
                # Event handlers
                add_btn.click(
                    fn=lambda url, name: add_feed(url, name)[1],
                    inputs=[feed_url, feed_name],
                    outputs=add_result
                )
                
                remove_btn.click(
                    fn=lambda url: remove_feed(url)[1],
                    inputs=remove_url,
                    outputs=remove_result
                )
                
                refresh_btn.click(
                    fn=get_feeds_display,
                    outputs=feeds_display
                )
            
            # Processing Tab
            with gr.Tab("Process Feeds"):
                gr.Markdown("### Process RSS Feeds")
                gr.Markdown("Click the button below to fetch articles from all configured RSS feeds and generate summaries.")
                
                process_btn = gr.Button("Process Feeds", variant="primary", size="lg")
                progress_text = gr.Textbox(label="Progress", interactive=False, lines=2)
                process_result = gr.Textbox(label="Results", interactive=False, lines=10)
                
                def process_with_progress():
                    result = process_feeds(lambda msg: progress_text.update(value=msg))
                    return result, "Processing complete!"
                
                process_btn.click(
                    fn=process_feeds,
                    outputs=process_result
                )
            
            # View Results Tab
            with gr.Tab("View Results"):
                gr.Markdown("### Recent Summaries")
                
                with gr.Row():
                    limit_slider = gr.Slider(minimum=5, maximum=50, value=10, step=5, label="Number of articles to show")
                    refresh_summaries_btn = gr.Button("Refresh")
                
                summaries_display = gr.Textbox(
                    label="Recent Articles",
                    value=get_recent_summaries(),
                    interactive=False,
                    lines=20
                )
                
                refresh_summaries_btn.click(
                    fn=get_recent_summaries,
                    inputs=limit_slider,
                    outputs=summaries_display
                )
                
                gr.Markdown("### File Locations")
                gr.Markdown(f"- **CSV File**: `{csv_file}`")
                gr.Markdown(f"- **JSON File**: `{json_file}`")
                gr.Markdown(f"- **Feeds Config**: `{feeds_file}`")
    
    return iface

if __name__ == "__main__":
    # Create initial feeds file with sample feed if it doesn't exist
    if not os.path.exists(feeds_file):
        sample_feeds = [
            {"url": "https://news.ycombinator.com/rss", "name": "Hacker News"}
        ]
        save_feeds(sample_feeds)
    
    # Launch Gradio interface
    iface = create_gradio_interface()
    iface.launch(share=False, server_name="0.0.0.0", server_port=7860)