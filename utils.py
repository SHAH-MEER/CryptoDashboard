import streamlit as st
import requests
import pandas as pd
import time # Can be used for potential retries, though not implemented here yet

# --- Constants ---
CG_BASE_URL = "https://api.coingecko.com/api/v3"

# --- API Helper Functions ---

@st.cache_data(ttl=3600 * 6) # Cache for 6 hours
def get_coin_list():
    """Fetches the list of all coins from CoinGecko."""
    url = f"{CG_BASE_URL}/coins/list?include_platform=false"
    try:
        response = requests.get(url)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        # Create a mapping of display name (lowercase) to coin ID
        return {coin['name'].lower(): coin['id'] for coin in data}
    except requests.exceptions.HTTPError as http_err:
        # Specifically check for 429 Rate Limit error
        if response.status_code == 429:
            st.warning("Rate limit hit fetching coin list. Data might be stale. Please wait.")
        else:
            st.error(f"HTTP error fetching coin list: {http_err} (Status code: {response.status_code})")
        return {}
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching coin list: {e}")
        return {}
    except Exception as e:
        st.error(f"An unexpected error occurred processing the coin list: {e}")
        return {}

@st.cache_data(ttl=600) # Cache for 10 minutes (Increased from 60s)
def get_top_coins(currency, per_page=25):
    """Fetches market data for top N coins for the dashboard."""
    url = f"{CG_BASE_URL}/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page={per_page}&page=1&sparkline=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        # Ensure essential columns exist, adding them with NA/None if missing
        required_cols = ['id', 'name', 'symbol', 'current_price', 'price_change_percentage_24h',
                         'market_cap', 'total_volume', 'market_cap_rank', 'sparkline_in_7d']
        for col in required_cols:
            if col not in df.columns:
                if col == 'sparkline_in_7d':
                    df[col] = [None] * len(df) # Sparkline needs a list structure
                else:
                    df[col] = pd.NA # Use pandas NA for missing numeric/object data
        
        # Safely extract sparkline data
        df['sparkline_7d_prices'] = df['sparkline_in_7d'].apply(
            lambda x: x['price'] if isinstance(x, dict) and 'price' in x else None
        )
        return df
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 429:
            st.warning(f"Rate limit hit fetching top coins data. Showing stale data if available, or empty. Please wait. (Status: {response.status_code})")
        else:
            st.error(f"HTTP error fetching top coins: {http_err} (Status code: {response.status_code})")
        return pd.DataFrame() # Return empty dataframe on error
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching top coins: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred processing top coins: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=7200) # Cache for 2 hours
def get_historical_data(coin_id, currency, days):
    """Fetches historical price and volume data for a specific coin."""
    # Note: Can fetch 'prices', 'market_caps', 'total_volumes'
    url = f"{CG_BASE_URL}/coins/{coin_id}/market_chart?vs_currency={currency}&days={days}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Process prices
        prices = data.get("prices", [])
        df_prices = pd.DataFrame(prices, columns=["timestamp", "price"])
        
        # Process volumes (optional, but good to include if available)
        volumes = data.get("total_volumes", [])
        df_volumes = pd.DataFrame(volumes, columns=["timestamp", "volume"])

        # Merge prices and volumes
        if not df_prices.empty and not df_volumes.empty:
            df_hist = pd.merge(df_prices, df_volumes, on="timestamp", how="inner")
        elif not df_prices.empty:
             df_hist = df_prices
             df_hist['volume'] = 0 # Add volume column if only prices available
        else:
            return pd.DataFrame(columns=["date", "price", "volume"]) # Return empty if no price data

        df_hist["date"] = pd.to_datetime(df_hist["timestamp"], unit="ms")
        # Ensure correct types and handle potential NaNs from merge/missing data
        df_hist["price"] = pd.to_numeric(df_hist["price"], errors='coerce')
        df_hist["volume"] = pd.to_numeric(df_hist["volume"], errors='coerce')
        df_hist = df_hist.dropna(subset=['price']) # Cannot proceed without price
        df_hist['volume'] = df_hist['volume'].fillna(0) # Fill missing volumes with 0

        # Select and order columns, set index for time series operations if needed by caller
        df_hist = df_hist[["date", "price", "volume"]].sort_values(by='date').drop_duplicates(subset=['date'])
        
        return df_hist

    except requests.exceptions.HTTPError as http_err:
        status_code = response.status_code
        if status_code == 429:
             st.warning(f"Rate limit hit fetching historical data for {coin_id}. Please wait.")
        elif status_code == 401:
             st.error(f"Error 401: Unauthorized. Fetching 'max' historical data may require a paid API key.")
        elif status_code == 404:
            st.warning(f"Historical data not found for {coin_id} ({status_code}).")
        else:
             st.warning(f"Could not fetch historical data for {coin_id} (HTTP Error {status_code}).")
        return pd.DataFrame(columns=["date", "price", "volume"])
    except requests.exceptions.RequestException as e:
        st.warning(f"Network error fetching historical data for {coin_id}: {e}")
        return pd.DataFrame(columns=["date", "price", "volume"])
    except (KeyError, TypeError, ValueError) as e: # Catch data processing errors
        st.warning(f"Historical data format unexpected or processing error for {coin_id}: {e}")
        return pd.DataFrame(columns=["date", "price", "volume"])


@st.cache_data(ttl=300) # Cache for 5 minutes
def get_global_market_data():
    """Fetches global market data."""
    url = f"{CG_BASE_URL}/global"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['data'] # The actual data is nested under the 'data' key
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 429:
             st.warning(f"Rate limit hit fetching global market data. Please wait.")
        else:
             st.warning(f"Could not fetch global market data (HTTP Error {response.status_code}).")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching global market data: {e}")
        return None
    except KeyError:
        st.error("Unexpected format received from global market data API.")
        return None


@st.cache_data(ttl=300) # Cache for 5 minutes
def get_coin_details(coin_id):
    """Fetches detailed data for a specific coin ID."""
    url = f"{CG_BASE_URL}/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        status_code = response.status_code
        if status_code == 429:
            st.error(f"Rate limit hit fetching details for {coin_id}. Please wait.")
        elif status_code == 404:
             st.error(f"Could not find details for coin ID: {coin_id}. It might be delisted or invalid.")
        else:
            st.error(f"HTTP error fetching details for {coin_id}: {http_err} (Status: {status_code})")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching details for {coin_id}: {e}")
        return None
    except Exception as e:
         st.error(f"An unexpected error occurred processing details for {coin_id}: {e}")
         return None

@st.cache_data(ttl=7200) # Cache for 2 hours
def get_ohlc_data(coin_id, currency, days):
    """Fetches OHLC data for candlestick charts."""
    url = f"{CG_BASE_URL}/coins/{coin_id}/ohlc?vs_currency={currency}&days={days}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # OHLC data format: [timestamp, open, high, low, close]
        df_ohlc = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df_ohlc['date'] = pd.to_datetime(df_ohlc['timestamp'], unit='ms')
        # Ensure numeric types and drop rows where conversion fails
        for col in ['open', 'high', 'low', 'close']:
             df_ohlc[col] = pd.to_numeric(df_ohlc[col], errors='coerce')
        df_ohlc = df_ohlc.dropna(subset=['open', 'high', 'low', 'close']) # Need all OHLC values
        # Select and order final columns
        df_ohlc = df_ohlc[['date', 'open', 'high', 'low', 'close', 'timestamp']]
        return df_ohlc
    except requests.exceptions.HTTPError as http_err:
        status_code = response.status_code
        if status_code == 429:
             st.warning(f"Rate limit hit fetching OHLC data for {coin_id}. Please wait.")
        elif status_code == 401:
             st.error(f"Error 401: Unauthorized. Fetching OHLC data might require a paid API key for certain coins/ranges.")
        elif status_code == 404:
            st.warning(f"OHLC data not found for {coin_id} ({status_code}).")
        else:
             st.warning(f"Could not fetch OHLC data for {coin_id} (HTTP Error {status_code}).")
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'timestamp'])
    except requests.exceptions.RequestException as e:
        st.warning(f"Network error fetching OHLC data for {coin_id}: {e}")
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'timestamp'])
    except Exception as e: # Catch potential JSON errors or DataFrame issues
        st.error(f"An unexpected error occurred processing OHLC data for {coin_id}: {e}")
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'timestamp'])


@st.cache_data(ttl=180) # Cache for 3 minutes (As used in Gainers/Losers)
def get_market_data_for_gainers_losers(currency, num_coins=250):
    """Fetches market data specifically for Gainers/Losers page."""
    url = f"{CG_BASE_URL}/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page={num_coins}&page=1&sparkline=false&price_change_percentage=24h"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Check if data is a list (expected)
        if not isinstance(data, list):
             st.error(f"Unexpected data format received from market data endpoint (expected list, got {type(data)}).")
             return pd.DataFrame()

        # Select and rename columns for clarity
        required_cols = ['name', 'symbol', 'current_price', 'price_change_percentage_24h', 'total_volume']
        # Filter data to include only entries that are dicts and have all required keys
        filtered_data = [d for d in data if isinstance(d, dict) and all(k in d for k in required_cols)]
        
        if not filtered_data:
            st.warning("No valid coin data found in the response.")
            return pd.DataFrame()

        df = pd.DataFrame(filtered_data)[required_cols]
        
        df.rename(columns={
            'price_change_percentage_24h': 'change_24h',
            'current_price': 'price'
        }, inplace=True)

        # Ensure numeric types, coercing errors
        df['change_24h'] = pd.to_numeric(df['change_24h'], errors='coerce')
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce')
        
        # Drop rows where essential data (like 'change_24h') couldn't be converted or is missing
        df = df.dropna(subset=['change_24h', 'price']) 
        return df
        
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 429:
             st.warning(f"Rate limit hit fetching market data. Please wait.")
        else:
             st.warning(f"Could not fetch market data (HTTP Error {response.status_code}).")
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching market data: {e}")
        return pd.DataFrame()
    except Exception as e: # Catch potential JSON parsing or DataFrame errors
        st.error(f"An error occurred processing market data: {e}")
        return pd.DataFrame() 

@st.cache_data(ttl=60) # Cache prices for 60 seconds
def get_current_prices(coin_ids, currency='usd'):
    """Fetches the current price for a list of coin IDs."""
    if not coin_ids:
        return {}
    
    # Ensure coin_ids are strings and handle potential non-string items gracefully
    valid_coin_ids = [str(id) for id in coin_ids if isinstance(id, (str, int)) and str(id).strip()] # Basic validation
    if not valid_coin_ids:
        st.warning("No valid coin IDs provided to fetch prices.")
        return {}
        
    ids_string = ",".join(valid_coin_ids)
    url = f"{CG_BASE_URL}/simple/price?ids={ids_string}&vs_currencies={currency}"
    
    prices = {}
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Extract price for each coin_id, handling cases where a specific ID might be missing
        for coin_id in valid_coin_ids:
            prices[coin_id] = data.get(coin_id, {}).get(currency)
            if prices[coin_id] is None:
                st.warning(f"Could not retrieve price for coin ID: {coin_id} in {currency.upper()}. It might be delisted or not available in this currency.")
        return prices
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 429:
            st.warning(f"Rate limit hit fetching prices. Price data might be stale or incomplete. Please wait.")
        else:
            st.warning(f"Could not fetch prices (HTTP Error {response.status_code}). Some prices may be missing.")
        # Return potentially partial data or empty dict even on HTTP errors
        # Attempt to salvage any prices received before the error
        if isinstance(data, dict):
             for coin_id in valid_coin_ids:
                 if coin_id not in prices: # Only add if not already processed
                     prices[coin_id] = data.get(coin_id, {}).get(currency)
        return prices
    except requests.exceptions.RequestException as e:
        st.warning(f"Network error fetching prices: {e}. Prices may be missing.")
        return prices # Return empty or partial dict
    except Exception as e:
        st.error(f"An unexpected error occurred fetching prices: {e}")
        return prices # Return empty or partial dict 