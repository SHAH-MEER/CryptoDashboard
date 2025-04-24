import streamlit as st

st.set_page_config(
    page_title="Crypto Dashboard Home",
    page_icon="💰",
    layout="wide"
)

st.title("Welcome to the Crypto Dashboard! 💰")

st.markdown("""
### About This Application

This application serves as an interactive dashboard for exploring cryptocurrency data. 
It fetches real-time and historical information directly from the **CoinGecko API**.

---

### How to Use

**👈 Select a page from the sidebar** on the left to navigate through the different sections of the dashboard.

---

### Available Pages

Currently, the following pages are available:

1.  **📈 Dashboard:**
    *   Displays a table of top cryptocurrencies by market capitalization (with 7d sparklines).
    *   Provides analysis and details in **tabs** ("📊 Market Visuals", "🔎 Selected Coin Detail").
    *   *Market Visuals Tab:* Shows 24h change bar chart, Market Cap/Volume scatter plot, and distribution pie charts for Market Cap & Volume.
    *   *Selected Coin Detail Tab:* Allows selecting a coin from the table and viewing its key metrics and historical price chart (in nested tabs).
    *   Allows customization of the currency and number of coins displayed.

2.  **🌍 Global Market:**
    *   Shows key global crypto metrics (Total Market Cap, 24h Volume, Active Coins).
    *   Includes a Gauge chart for Bitcoin (BTC) dominance.
    *   Visualizes market dominance distribution with a pie chart and a treemap.

3.  **🔎 Coin Detail:**
    *   Search for any coin (defaults to Bitcoin) and view comprehensive details within **tabs** ("📊 Market Overview", "📈 Charts", "ℹ️ Info & Links").
    *   Displays price, market cap, volume, ATH/ATL data, recent performance metrics.
    *   Shows supply information (Circulating, Total, Max) with a distribution pie chart.
    *   Includes a 7-day sparkline, coin description, and official links.
    *   Provides customizable historical price charts (Line or Candlestick) with **overlayed volume bars**.

4.  **⏳ Time Series Analysis:**
    *   Performs basic time series analysis on a selected coin, organized into **tabs** ("📈 Price & Moving Averages", "📊 Returns Analysis", "📉 Decomposition & Autocorrelation").
    *   Plots price with Simple Moving Averages (**SMA**) or Exponential Moving Averages (**EMA**).
    *   Plots daily percentage returns and shows a histogram of their distribution.
    *   Includes a rolling volatility plot (30-day standard deviation).
    *   Displays basic return statistics.
    *   Plots seasonal decomposition (Trend, Seasonal, Residual components).
    *   Plots **ACF/PACF** for either **Daily Returns** or **Price** (differenced if non-stationary).

5.  **💹 Gainers & Losers:**
    *   Shows the top N gainers and losers (from the top 250 coins) over the last 24 hours.
    *   Displays results in tables and corresponding bar charts for both % change and volume.
    *   Highlights the single biggest gainer and loser using metrics.
    *   Includes a scatter plot visualizing the relationship between 24h Change (%) and 24h Volume.

6.  **🔮 Forecasting & Analysis:**
    *   Provides time series forecasting and analysis using different models/techniques in separate tabs.
    *   Allows selecting a coin, currency, historical training period, and forecast horizon (where applicable).
    *   **Prophet Tab:** Uses Facebook Prophet, displaying forecast plot (actuals, prediction, uncertainty) and component plots (trend, seasonality).
    *   **ARIMA Tab:** Performs stationarity test (ADF), fits a basic ARIMA model (order typically (5,1,0) or (5,0,0)), displays forecast plot with confidence intervals.
    *   **Autocorrelation Tab:** Calculates and plots the Autocorrelation Function (ACF) and Partial Autocorrelation Function (PACF) for daily returns to identify potential time series patterns.
    *   Includes an important disclaimer about the speculative nature of crypto forecasting.

7.  **📰 News & Sentiment:**
    *   Fetches recent news articles related to a search query (e.g., a specific cryptocurrency) from NewsAPI.org.
    *   Requires user to provide their own NewsAPI key (input in sidebar).
    *   Analyzes the sentiment (Positive/Negative/Neutral) of each article's title and description using NLTK VADER.
    *   Displays articles with links and their corresponding sentiment score/label.
    *   Shows an overall sentiment distribution bar chart in the sidebar.

---

*Note: The CoinGecko API has rate limits on its free tier. If you encounter errors (especially a 429 error), please wait a minute before trying again.*
""")

st.sidebar.success("Select a page above.") 