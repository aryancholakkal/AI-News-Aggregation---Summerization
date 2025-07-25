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
                        'Summary': f'📝 View Summary',  # This will be clickable
                        'Original URL': f'🔗 Open URL'   # This will be clickable
                    })
                return pd.DataFrame(df_data)
            else:
                return pd.DataFrame({'Error': [f"Failed to fetch articles: {response.status_code}"]})
        except Exception as e:
            return pd.DataFrame({'Error': [f"Connection error: {str(e)}"]})
    
    def get_article_summary(self, selected_row: int) -> tuple:
        """Get summary for selected article - returns (summary_text, modal_visibility)"""
        try:
            if selected_row is None or selected_row < 1 or selected_row > len(self.articles_data):
                return "Please select a valid article row number.", gr.update(visible=False)
            
            article_id = selected_row
            response = requests.get(f"{FASTAPI_BASE_URL}/api/article/{article_id}/summary")
            if response.status_code == 200:
                data = response.json()
                article = self.articles_data[selected_row - 1]
                summary_text = f"**{article['title']}**\n\n{data['summary']}"
                return summary_text, gr.update(visible=True)
            else:
                error_text = f"Error fetching summary: {response.status_code}"
                return error_text, gr.update(visible=True)
        except Exception as e:
            error_text = f"Error: {str(e)}"
            return error_text, gr.update(visible=True)
    
    def open_original_url(self, selected_row: int) -> str:
        """Open original URL for selected article"""
        try:
            if selected_row is None or selected_row < 1 or selected_row > len(self.articles_data):
                return "Please select a valid article row number."
            
            article = self.articles_data[selected_row - 1]
            webbrowser.open(article['url'])
            return f"✅ Opened: {article['title']}"
        except Exception as e:
            return f"❌ Error opening URL: {str(e)}"
    
    def handle_table_select(self, evt: gr.SelectData):
        """Handle table cell selection"""
        row_index = evt.index[0]
        col_index = evt.index[1]
        
        if col_index == 2:  # Summary column
            return self.get_article_summary(row_index + 1)
        elif col_index == 3:  # URL column
            url_result = self.open_original_url(row_index + 1)
            return url_result, gr.update(visible=False)
        
        return "", gr.update(visible=False)
    
    def close_modal(self):
        """Close the modal"""
        return gr.update(visible=False)
    
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
                        'Action': '🗑️ Remove'  # This will be clickable
                    })
                return pd.DataFrame(df_data)
            else:
                return pd.DataFrame({'Error': [f"Failed to fetch feeds: {response.status_code}"]})
        except Exception as e:
            return pd.DataFrame({'Error': [f"Connection error: {str(e)}"]})
    
    def handle_feeds_table_select(self, evt: gr.SelectData):
        """Handle feeds table cell selection"""
        row_index = evt.index[0]
        col_index = evt.index[1]
        
        if col_index == 3:  # Action column (Remove)
            return self.remove_feed(row_index + 1)
        
        return ""
    
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
    
    # Custom CSS for better styling and modal
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
    /* Make certain table cells look clickable */
    .dataframe td:nth-child(3), .dataframe td:nth-child(4) {
        cursor: pointer;
        color: #007bff;
        text-decoration: underline;
    }
    .dataframe td:nth-child(3):hover, .dataframe td:nth-child(4):hover {
        background-color: #f8f9fa;
        color: #0056b3;
    }
    /* Modal styling */
        .modal-content {
            background: #fff;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            max-width: 800px;
            max-height: 70vh;
            overflow-y: auto;
            margin: 0 auto; /* Center horizontally */
            color: #000;
        }

        .modal-content h2, .modal-content p {
            color: #000;
        }

        .modal-group {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

    .close-button {
        float: right;
        margin-top:1px;
        max-width: 50px;
    }
    """
    
    with gr.Blocks(css=css, title="RSS Feed Summarizer") as demo:
        gr.Markdown("# 📰 RSS Feed Summarizer")
        gr.Markdown("*Automated RSS feed processing and article summarization (Runs weekly)*")
        
        with gr.Tabs():
            # View Results Tab (Default/Landing Page)
            with gr.TabItem("📊 View Results", id=0):
                gr.Markdown("## Recent Articles")
                gr.Markdown("*Click on '📝 View Summary' to see article summary in modal, or '🔗 Open URL' to open original article*")
                
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh Articles", variant="primary")
                
                # 4-column table with clickable Summary and URL columns
                articles_table = gr.Dataframe(
                    value=app.get_articles(),
                    headers=["Sl. No", "Title", "Summary", "Original URL"],
                    interactive=False,
                    wrap=True
                )
                
                # Modal for displaying summary
                with gr.Group(visible=False) as modal:
                    with gr.Row():
                        gr.Markdown("## 📖 Article Summary")
                        close_modal_btn = gr.Button("❌ Close", variant="stop", size="sm", elem_classes=["close-button"])
                    
                    summary_display = gr.Markdown(
                        value="",
                        elem_classes=["modal-content"]
                    )
                
                # Status display for URL operations
                url_status = gr.Textbox(
                    label="Status",
                    lines=1,
                    placeholder="Status messages will appear here...",
                    visible=False
                )
                
                # Event handlers for View Results tab
                refresh_btn.click(
                    app.refresh_articles,
                    outputs=[articles_table]
                )
                
                # Handle table cell clicks
                def handle_table_click(evt: gr.SelectData):
                    row_index = evt.index[0]
                    col_index = evt.index[1]
                    
                    if col_index == 2:  # Summary column
                        summary_text, modal_visibility = app.get_article_summary(row_index + 1)
                        return summary_text, modal_visibility, gr.update(visible=False)
                    elif col_index == 3:  # URL column
                        url_result = app.open_original_url(row_index + 1)
                        return "", gr.update(visible=False), gr.update(value=url_result, visible=True)
                    
                    return "", gr.update(visible=False), gr.update(visible=False)
                
                articles_table.select(
                    handle_table_click,
                    outputs=[summary_display, modal, url_status]
                )
                
                close_modal_btn.click(
                    app.close_modal,
                    outputs=[modal]
                )
            
            # Manage Feeds Tab
            with gr.TabItem("⚙️ Manage Feeds"):
                gr.Markdown("## Manage RSS Feeds")
                gr.Markdown("*Click on '🗑️ Remove' to delete a feed*")
                
                with gr.Row():
                    # Left side - Current Feeds Table
                    with gr.Column(scale=3):
                        gr.Markdown("### Current Feeds")
                        
                        with gr.Row():
                            refresh_feeds_btn = gr.Button("🔄 Refresh Feeds", variant="primary")
                        
                        feeds_table = gr.Dataframe(
                            value=app.get_feeds(),
                            headers=["Sl. No", "Name", "URL", "Action"],
                            interactive=True,
                            wrap=True
                        )
                        
                        feeds_status = gr.Textbox(
                            label="Status",
                            lines=2,
                            placeholder="Feed operation status will appear here.",
                            visible=False
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
                
                # Handle feeds table cell clicks
                def handle_feeds_table_click(evt: gr.SelectData):
                    row_index = evt.index[0]
                    col_index = evt.index[1]
                    
                    if col_index == 3:  # Action column (Remove)
                        result = app.remove_feed(row_index + 1)
                        return result, gr.update(visible=True), app.refresh_feeds()
                    
                    return "", gr.update(visible=False), gr.update()
                
                feeds_table.select(
                    handle_feeds_table_click,
                    outputs=[feeds_status, feeds_status, feeds_table]
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
                - **Clickable Table**: Click directly on table cells to view summaries or open URLs
                - **Modal Display**: Article summaries appear in elegant modal popups
                - **Multiple Formats**: Saves data in both CSV and JSON formats
                - **Web Interface**: User-friendly interface for managing feeds and viewing results
                
                ### How to Use:
                1. **View Results**: See recent articles in the table
                2. **View Summaries**: Click on "📝 View Summary" in the table to see article summary in a modal
                3. **Open URLs**: Click on "🔗 Open URL" to open the original article
                4. **Manage Feeds**: Add new feeds or remove existing ones by clicking "🗑️ Remove"
                5. The system automatically processes feeds weekly
                
                ### Technical Details:
                - Backend: FastAPI with automatic weekly scheduling
                - Frontend: Gradio interface with interactive tables and modals
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