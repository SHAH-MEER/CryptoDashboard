# 💰 Crypto Dashboard

An interactive multi-page dashboard for exploring cryptocurrency data, built with Streamlit and powered by the CoinGecko API.

## Features

This dashboard provides several views:

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
    *   Generates time series forecasts and analysis using different models/techniques in separate tabs:
        *   **Prophet:** Uses Facebook Prophet, displaying forecast plot and component plots (trend, seasonality).
        *   **ARIMA:** Performs basic stationarity test, fits an ARIMA model (e.g., (5,1,0)), plots forecast with confidence intervals.
        *   **Autocorrelation:** Plots the ACF and PACF of daily returns to identify potential patterns.
    *   Allows selection of coin, currency, training period, and forecast horizon (where applicable).
    *   Includes an important disclaimer about the reliability of crypto forecasts.

7.  **📰 News & Sentiment:**
    *   Fetches recent news articles related to a search query (e.g., a specific cryptocurrency) from NewsAPI.org.
    *   Uses API key stored securely in `.streamlit/secrets.toml`.
    *   Analyzes the sentiment (Positive/Negative/Neutral) of each article's title and description using NLTK VADER.
    *   Displays articles with images, links, and their corresponding sentiment score/label.
    *   Shows an overall sentiment distribution bar chart in the sidebar.

8.  **💼 Portfolio Management:**
    *   Allows users to manually add cryptocurrency holdings (coin, quantity, optional purchase price).
    *   Stores portfolio data temporarily in the browser session.
    *   Fetches current prices via CoinGecko API.
    *   Displays total portfolio value and total Profit/Loss (P/L).
    *   Shows a detailed table of holdings with individual values and P/L.
    *   Includes visualizations: Pie chart for value distribution and Bar chart for P/L per holding.
    *   Provides a button to clear the session portfolio.

## Setup and Installation

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <your-repo-url>
    cd <repo-directory>
    ```

2.  **Create and activate a virtual environment:**
    *   **Using `venv`:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate  # On Windows use `venv\Scripts\activate`
        ```
    *   **Using `conda`:**
        ```bash
        conda create --name crypto_dash python=3.10  # Or your preferred Python version
        conda activate crypto_dash
        ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Installing `prophet` might require additional setup depending on your OS. Refer to the [Prophet installation guide](https://facebook.github.io/prophet/docs/installation.html) if you encounter issues.)*

## Running the App

Once the setup is complete, run the Streamlit application:

```bash
streamlit run app.py
```

The dashboard should open in your default web browser.

## Dependencies

All required Python packages are listed in `requirements.txt`.

## Disclaimer

The forecasting features provided are for educational and illustrative purposes only. Cryptocurrency markets are highly volatile and unpredictable. **Do not use these forecasts for financial decisions.** Past performance is not indicative of future results. 