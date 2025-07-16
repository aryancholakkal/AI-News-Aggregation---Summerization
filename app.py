import gradio as gr
import requests
import pandas as pd
import webbrowser
from typing import List, Dict, Any

# Configuration
FASTAPI_BASE_URL = "http://localhost:8000"

class GradioRSSApp:
    def __init__(self):
        self.articles_data = []
        self.feeds_data = []
        
    def get_articles(self, limit: int = 20) -> pd.DataFrame:
        """Fetch articles from FastAPI backend"""
        try:
            response = requests.get(f"{FASTAPI_BASE_URL}/api/articles?limit={limit}")
            if response.status_code == 200:
                self.articles_data = response.json()
                # Convert to DataFrame for table display - 4 columns as requested
                df_data = []
                for i, article in enumerate(self.articles_data, 1):
                    df_data.append({
                        'Sl. No': i,
                        'Title': article['title'],
                        'Summary': 'View Summary',  # Placeholder text for button column
                        'Original URL': 'Open URL'   # Placeholder text for button column
                    })
                return pd.DataFrame(df_data)
            else:
                return pd.DataFrame({'Error': [f"Failed to fetch articles: {response.status_code}"]})
        except Exception as e:
            return pd.DataFrame({'Error': [f"Connection error: {str(e)}"]})
    
    def get_article_summary(self, selected_row: int) -> str:
        """Get summary for selected article"""
        try:
            if selected_row is None or selected_row < 1 or selected_row > len(self.articles_data):
                return "Please select a valid article row number."
            
            article_id = selected_row
            response = requests.get(f"{FASTAPI_BASE_URL}/api/article/{article_id}/summary")
            if response.status_code == 200:
                data = response.json()
                article = self.articles_data[selected_row - 1]
                return f"**Title:** {article['title']}\n\n**Summary:** {data['summary']}"
            else:
                return f"Error fetching summary: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def open_original_url(self, selected_row: int) -> str:
        """Open original URL for selected article"""
        try:
            if selected_row is None or selected_row < 1 or selected_row > len(self.articles_data):
                return "Please select a valid article row number."
            
            article = self.articles_data[selected_row - 1]
            webbrowser.open(article['url'])
            return f"Opening: {article['url']}"
        except Exception as e:
            return f"Error opening URL: {str(e)}"
    
    def get_feeds(self) -> pd.DataFrame:
        """Fetch feeds from FastAPI backend"""
        try:
            response = requests.get(f"{FASTAPI_BASE_URL}/api/feeds")
            if response.status_code == 200:
                self.feeds_data = response.json()
                # Convert to DataFrame for table display
                df_data = []
                for feed in self.feeds_data:
                    df_data.append({
                        'Sl. No': feed['id'],
                        'Name': feed['name'],
                        'URL': feed['url'],
                        'Action': 'Remove'  # Placeholder for remove button
                    })
                return pd.DataFrame(df_data)
            else:
                return pd.DataFrame({'Error': [f"Failed to fetch feeds: {response.status_code}"]})
        except Exception as e:
            return pd.DataFrame({'Error': [f"Connection error: {str(e)}"]})
    
    def add_feed(self, url: str, name: str = "") -> str:
        """Add new RSS feed"""
        try:
            if not url.strip():
                return "Please enter a valid RSS feed URL."
            
            data = {
                "url": url.strip(),
                "name": name.strip() if name.strip() else url.strip()
            }
            
            response = requests.post(f"{FASTAPI_BASE_URL}/api/feeds", json=data)
            if response.status_code == 200:
                result = response.json()
                return f"✅ {result['message']}"
            else:
                error_data = response.json()
                return f"❌ Error: {error_data.get('detail', 'Unknown error')}"
        except Exception as e:
            return f"❌ Connection error: {str(e)}"
    
    def remove_feed(self, selected_row: int) -> str:
        """Remove selected feed"""
        try:
            if selected_row is None or selected_row < 1 or selected_row > len(self.feeds_data):
                return "Please select a valid feed row number."
            
            feed_id = selected_row
            response = requests.delete(f"{FASTAPI_BASE_URL}/api/feeds/{feed_id}")
            if response.status_code == 200:
                result = response.json()
                return f"✅ {result['message']}"
            else:
                error_data = response.json()
                return f"❌ Error: {error_data.get('detail', 'Unknown error')}"
        except Exception as e:
            return f"❌ Connection error: {str(e)}"
    
    def refresh_articles(self) -> pd.DataFrame:
        """Refresh articles table"""
        return self.get_articles()
    
    def refresh_feeds(self) -> pd.DataFrame:
        """Refresh feeds table"""
        return self.get_feeds()

def create_gradio_app():
    app = GradioRSSApp()
    
    # Custom CSS for better styling
    css = """
    .gradio-container {
        max-width: 1200px !important;
    }
    .tab-nav {
        background-color: #f8f9fa;
    }
    .selected {
        background-color: #007bff !important;
        color: white !important;
    }
    """
    
    with gr.Blocks(css=css, title="RSS Feed Summarizer") as demo:
        gr.Markdown("# 📰 RSS Feed Summarizer")
        gr.Markdown("*Automated RSS feed processing and article summarization (Runs weekly)*")
        
        with gr.Tabs():
            # View Results Tab (Default/Landing Page)
            with gr.TabItem("📊 View Results", id=0):
                gr.Markdown("## Recent Articles")
                
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh Articles", variant="primary")
                
                # 4-column table as requested
                articles_table = gr.Dataframe(
                    value=app.get_articles(),
                    headers=["Sl. No", "Title", "Summary", "Original URL"],
                    interactive=False,
                    wrap=True
                )
                
                with gr.Row():
                    with gr.Column(scale=1):
                        article_row_input = gr.Number(
                            label="Select Article Row Number",
                            minimum=1,
                            precision=0,
                            value=1
                        )
                    
                    with gr.Column(scale=1):
                        summary_btn = gr.Button("📝 View Summary", variant="secondary")
                        url_btn = gr.Button("🔗 Open Original URL", variant="secondary")
                
                with gr.Row():
                    summary_output = gr.Textbox(
                        label="Article Summary",
                        lines=10,
                        placeholder="Select an article and click 'View Summary' to see the summary here."
                    )
                
                with gr.Row():
                    url_status = gr.Textbox(
                        label="URL Status",
                        lines=1,
                        placeholder="URL opening status will appear here."
                    )
                
                # Event handlers for View Results tab
                refresh_btn.click(
                    app.refresh_articles,
                    outputs=[articles_table]
                )
                
                summary_btn.click(
                    app.get_article_summary,
                    inputs=[article_row_input],
                    outputs=[summary_output]
                )
                
                url_btn.click(
                    app.open_original_url,
                    inputs=[article_row_input],
                    outputs=[url_status]
                )
            
            # Manage Feeds Tab (Reorganized as requested)
            with gr.TabItem("⚙️ Manage Feeds"):
                gr.Markdown("## Manage RSS Feeds")
                
                with gr.Row():
                    # Left side - Current Feeds Table
                    with gr.Column(scale=3):
                        gr.Markdown("### Current Feeds")
                        
                        with gr.Row():
                            refresh_feeds_btn = gr.Button("🔄 Refresh Feeds", variant="primary")
                        
                        feeds_table = gr.Dataframe(
                            value=app.get_feeds(),
                            headers=["Sl. No", "Name", "URL", "Action"],
                            interactive=False,
                            wrap=True
                        )
                        
                        with gr.Row():
                            with gr.Column(scale=1):
                                feed_row_input = gr.Number(
                                    label="Select Feed Row Number to Remove",
                                    minimum=1,
                                    precision=0,
                                    value=1
                                )
                            
                            with gr.Column(scale=1):
                                remove_btn = gr.Button("🗑️ Remove Feed", variant="stop")
                        
                        remove_status = gr.Textbox(
                            label="Remove Status",
                            lines=2,
                            placeholder="Feed removal status will appear here."
                        )
                    
                    # Right side - Add New Feed Form
                    with gr.Column(scale=2):
                        gr.Markdown("### Add New Feed")
                        
                        with gr.Group():
                            new_feed_url = gr.Textbox(
                                label="RSS Feed URL",
                                placeholder="https://example.com/rss",
                                lines=1
                            )
                            
                            new_feed_name = gr.Textbox(
                                label="Feed Name (Optional)",
                                placeholder="My News Source",
                                lines=1
                            )
                            
                            add_btn = gr.Button("➕ Add Feed", variant="primary")
                            
                            add_status = gr.Textbox(
                                label="Add Status",
                                lines=3,
                                placeholder="Feed addition status will appear here."
                            )
                
                # Event handlers for Manage Feeds tab
                refresh_feeds_btn.click(
                    app.refresh_feeds,
                    outputs=[feeds_table]
                )
                
                remove_btn.click(
                    app.remove_feed,
                    inputs=[feed_row_input],
                    outputs=[remove_status]
                ).then(
                    app.refresh_feeds,
                    outputs=[feeds_table]
                )
                
                add_btn.click(
                    app.add_feed,
                    inputs=[new_feed_url, new_feed_name],
                    outputs=[add_status]
                ).then(
                    app.refresh_feeds,
                    outputs=[feeds_table]
                ).then(
                    lambda: ("", ""),  # Clear the input fields
                    outputs=[new_feed_url, new_feed_name]
                )
            
            # About Tab
            with gr.TabItem("ℹ️ About"):
                gr.Markdown("""
                ## About RSS Feed Summarizer
                
                This application automatically processes RSS feeds and generates AI-powered summaries of articles.
                
                ### Features:
                - **Automatic Processing**: Feeds are processed weekly (every Monday at 9:00 AM)
                - **AI Summaries**: Uses OpenAI GPT models to generate concise summaries
                - **Multiple Formats**: Saves data in both CSV and JSON formats
                - **Web Interface**: User-friendly interface for managing feeds and viewing results
                
                ### How to Use:
                1. **View Results**: See recent articles with summaries (Default landing page)
                2. **Manage Feeds**: Add or remove RSS feeds
                3. The system automatically processes feeds weekly
                
                ### Technical Details:
                - Backend: FastAPI with automatic weekly scheduling
                - Frontend: Gradio interface
                - AI Integration: OpenAI GPT models
                - Data Storage: CSV and JSON files
                
                ### Note:
                Make sure your FastAPI backend is running on `http://localhost:8000` before using this interface.
                """)
    
    return demo

def check_backend_connection():
    """Check if the FastAPI backend is running"""
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/api/articles?limit=1", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    # Check backend connection
    if not check_backend_connection():
        print("⚠️  Warning: Cannot connect to FastAPI backend at http://localhost:8000")
        print("Please make sure your FastAPI application is running first.")
        print("Run: python main.py")
        return
    
    print("✅ Backend connection successful!")
    print("🚀 Starting Gradio interface...")
    
    # Create and launch the Gradio app
    demo = create_gradio_app()
    
    # Launch the app
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_api=False,
        show_error=True,
        quiet=False
    )

if __name__ == "__main__":
    main()