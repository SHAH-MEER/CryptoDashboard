import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, date
import nltk
import plotly.express as px
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import ssl # For handling NLTK download context issues if they arise

# Set page config as the first Streamlit command
st.set_page_config(page_title="News & Sentiment", page_icon="📰", layout="wide")

# --- NLTK Setup --- 
# Attempt to set unverified context for NLTK download (may be needed on some systems)
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download VADER lexicon if not already present
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError: # Use LookupError for missing NLTK resources
    st.info("Downloading NLTK VADER lexicon for sentiment analysis...")
    try: 
        nltk.download('vader_lexicon', quiet=True)
        st.success("VADER lexicon downloaded successfully.")
    except Exception as e:
         st.error(f"Failed to download VADER lexicon automatically: {e}")
         st.error("Sentiment analysis may not work. Try running python -m nltk.downloader vader_lexicon in your terminal.")

@st.cache_resource # Cache the analyzer resource
def get_sentiment_analyzer():
    try:
        return SentimentIntensityAnalyzer()
    except LookupError: # If download failed above
        st.error("VADER lexicon not found. Sentiment analysis disabled.")
        return None

analyzer = get_sentiment_analyzer()

st.title("📰 News & Sentiment Analysis")
st.caption("Powered by NewsAPI.org")
st.markdown("Fetches recent news articles about cryptocurrencies (or any topic) and analyzes their sentiment.")

# --- Helper Functions ---
@st.cache_data(ttl=3600) # Cache news for 1 hour
def get_news(api_key, query, from_date, to_date, language='en', sort_by='publishedAt'):
    """Fetches news articles from NewsAPI."""
    base_url = "https://newsapi.org/v2/everything"
    params = {
        'q': query,
        'apiKey': api_key,
        'from': from_date,
        'to': to_date,
        'language': language,
        'sortBy': sort_by,
        'pageSize': 30
    }
    headers = {'User-Agent': 'CryptoDashboardStreamlitApp/1.0'} # Be polite
    
    articles = []
    error_message = None
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        
        if data.get('status') == 'ok':
            articles = data.get('articles', [])
            if not articles:
                 error_message = "No articles found for your query in the selected date range."
        else:
            error_message = f"API Error: {data.get('code')} - {data.get('message', 'Unknown error')}"
            
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401: # Unauthorized
            error_message = "API Error 401: Invalid API Key. Please check the key provided."
        elif response.status_code == 429: # Too Many Requests
            error_message = "API Error 429: Rate limit hit. Please wait and try again later."
        else:
            error_message = f"HTTP Error: {http_err}"
    except requests.exceptions.RequestException as e:
        error_message = f"Network Error fetching news: {e}"
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        
    return articles, error_message

def analyze_sentiment(text):
    if analyzer is None or not text:
        return {'compound': 0, 'label': 'Neutral'} # Default if analyzer failed or text is empty
    
    vs = analyzer.polarity_scores(text)
    compound_score = vs['compound']
    
    if compound_score >= 0.05:
        label = 'Positive'
    elif compound_score <= -0.05:
        label = 'Negative'
    else:
        label = 'Neutral'
        
    return {'compound': compound_score, 'label': label}

# --- Sidebar --- 
st.sidebar.header("📰 News Search Options")

# Search Term
search_query = st.sidebar.text_input("Search Topic (e.g., Bitcoin, Ethereum):", "Bitcoin")

# Date Range
today = date.today()
default_from_date = today - timedelta(days=7) # Default to last 7 days

col1_side, col2_side = st.sidebar.columns(2)
with col1_side:
    from_date = st.date_input("From Date", value=default_from_date, max_value=today)
with col2_side:
    to_date = st.date_input("To Date", value=today, min_value=from_date, max_value=today)

# Trigger Button
fetch_news_button = st.sidebar.button("Fetch News & Analyze Sentiment", key="fetch_news")

# --- Main Page Display --- 

if fetch_news_button:
    # Fetch API key from secrets
    api_key = st.secrets["newsapi_key"]

    if not api_key:
        st.error("API Key not found in secrets. Please add it to `.streamlit/secrets.toml` as `newsapi_key = 'YOUR_KEY'`.")
    elif not search_query:
        st.warning("Please enter a search topic in the sidebar.")
    elif from_date > to_date:
         st.error("'From Date' cannot be after 'To Date'.")
    else:
        with st.spinner(f"Fetching news for '{search_query}'..."):
            articles, error = get_news(api_key, search_query, from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d"))

        if error:
            st.error(error)
        elif articles:
            st.success(f"Found {len(articles)} articles.")
            st.markdown("--- ")
            
            sentiments = []
            for article in articles:
                title = article.get('title', '')
                description = article.get('description', '')
                image_url = article.get('urlToImage') # Get image URL
                content_to_analyze = (title if title else '') + ". " + (description if description else '')
                
                sentiment = analyze_sentiment(content_to_analyze)
                sentiments.append(sentiment['compound']) # Store compound score
                
                # Display Article
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.subheader(title if title else "No Title")
                    st.caption(f"Source: {article.get('source', {}).get('name', 'N/A')} | Published: {pd.to_datetime(article.get('publishedAt')).strftime('%Y-%m-%d %H:%M') if article.get('publishedAt') else 'N/A'}")
                    # Display image if URL exists
                    if image_url:
                        try:
                            # Set a fixed width for the image
                            st.image(image_url, width=300) 
                        except Exception as e:
                             st.warning(f"Could not load image: {e}") # Handle potential image loading errors
                    st.write(description if description else "*No description available.*")
                    st.link_button("Read Article", article.get('url', '#'))
                with col2:
                     # Display Sentiment Label & Score
                     color = "gray" 
                     if sentiment['label'] == 'Positive': color = "green"
                     elif sentiment['label'] == 'Negative': color = "red"
                     st.markdown(f"**Sentiment:** <span style='color:{color};'>**{sentiment['label']}**</span>", unsafe_allow_html=True)
                     st.metric(label="Compound Score", value=f"{sentiment['compound']:.3f}")
                
                st.markdown("--- ")
            
            # Overall Sentiment Visualization
            st.sidebar.markdown("--- ")
            st.sidebar.subheader("Overall Sentiment Distribution")
            if sentiments:
                 avg_sentiment = sum(sentiments) / len(sentiments)
                 pos_count = sum(1 for s in sentiments if s >= 0.05)
                 neg_count = sum(1 for s in sentiments if s <= -0.05)
                 neu_count = len(sentiments) - pos_count - neg_count
                 
                 st.sidebar.metric("Average Compound Score", f"{avg_sentiment:.3f}")
                 
                 sentiment_counts = pd.DataFrame({
                     'Sentiment': ['Positive', 'Neutral', 'Negative'],
                     'Count': [pos_count, neu_count, neg_count]
                 })
                 fig_sentiment_dist = px.bar(sentiment_counts, x='Sentiment', y='Count', 
                                             color='Sentiment', 
                                             color_discrete_map={'Positive':'green', 'Neutral':'grey', 'Negative':'red'},
                                             title="Article Sentiment Counts")
                 st.sidebar.plotly_chart(fig_sentiment_dist, use_container_width=True)
                 
            else:
                 st.sidebar.info("No articles to analyze sentiment.")

        else:
            # Should be caught by error handling in get_news, but as a fallback
            st.info("No articles found.")
else:
    st.info("Configure search options in the sidebar and click 'Fetch News & Analyze Sentiment'.") 