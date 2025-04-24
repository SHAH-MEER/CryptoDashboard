import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # Import graph_objects for Candlestick
from datetime import datetime
from plotly.subplots import make_subplots

st.set_page_config(page_title="Coin Detail", page_icon="🔎", layout="wide")

st.title("🔎 Coin Detail Page")

# --- Helper Functions ---

# Cache the list of all coins from CoinGecko
@st.cache_data(ttl=3600 * 6) # Cache for 6 hours
def get_coin_list():
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Create a mapping from lowercase name to id for easier lookup
        return {coin['name'].lower(): coin['id'] for coin in data}
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching coin list: {e}")
        return {}
    except Exception as e: # Catch potential JSON errors or others
        st.error(f"An error occurred processing the coin list: {e}")
        return {}

# Fetch detailed data for a specific coin ID
@st.cache_data(ttl=300) # Cache for 5 minutes
def get_coin_details(coin_id):
    # Include localization=false and sparkline=true for more data
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 429:
            st.error(f"Rate limit hit fetching details for {coin_id}. Please wait.")
        elif response.status_code == 404:
             st.error(f"Could not find details for coin ID: {coin_id}. It might be delisted or invalid.")
        else:
            st.error(f"HTTP error fetching details for {coin_id}: {http_err}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching details for {coin_id}: {e}")
        return None
    except Exception as e:
         st.error(f"An error occurred processing details for {coin_id}: {e}")
         return None

# Re-use historical data function (could be moved to a utility file later)
@st.cache_data(ttl=7200)
def get_historical_data(coin_id, currency, days):
    # Fetch price and volume data
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={currency}&days={days}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        prices = data.get("prices", [])
        volumes = data.get("total_volumes", []) # Get volumes
        
        df_prices = pd.DataFrame(prices, columns=["timestamp", "price"])
        df_volumes = pd.DataFrame(volumes, columns=["timestamp", "volume"])
        
        # Merge prices and volumes on timestamp
        df_hist = pd.merge(df_prices, df_volumes, on="timestamp", how="inner")
        
        df_hist["date"] = pd.to_datetime(df_hist["timestamp"], unit="ms")
        df_hist = df_hist.drop_duplicates(subset=['date']).sort_values(by='date')
        # Keep date for plotting, maybe index later if needed by other funcs
        df_hist = df_hist[["date", "price", "volume"]]
        return df_hist 
    except requests.exceptions.HTTPError as http_err:
        status_code = response.status_code
        if status_code == 429:
             st.warning(f"Rate limit hit fetching historical data. Please wait.")
        elif status_code == 401:
             st.error(f"Error 401: Unauthorized. Fetching 'max' historical data may require a paid CoinGecko API key.")
        elif status_code == 404:
            st.warning(f"Historical data not found for this period ({status_code}).")
        else:
             st.warning(f"Could not fetch historical data (HTTP Error {status_code}).")
        return pd.DataFrame(columns=["date", "price", "volume"])
    except requests.exceptions.RequestException as e:
        st.warning(f"Error fetching historical data: {e}")
        return pd.DataFrame(columns=["date", "price", "volume"])
    except KeyError:
        st.warning("Historical data format unexpected or missing.")
        return pd.DataFrame(columns=["date", "price", "volume"])

# New function to fetch OHLC data for candlestick charts
@st.cache_data(ttl=7200)
def get_ohlc_data(coin_id, currency, days):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency={currency}&days={days}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # OHLC data format: [timestamp, open, high, low, close]
        df_ohlc = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df_ohlc['date'] = pd.to_datetime(df_ohlc['timestamp'], unit='ms')
        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close']:
             df_ohlc[col] = pd.to_numeric(df_ohlc[col], errors='coerce')
        df_ohlc = df_ohlc.dropna()
        return df_ohlc
    except requests.exceptions.HTTPError as http_err:
        status_code = response.status_code
        if status_code == 429:
             st.warning(f"Rate limit hit fetching OHLC data. Please wait.")
        elif status_code == 401:
             st.error(f"Error 401: Unauthorized. Fetching 'max' OHLC data may require a paid API key.")
        elif status_code == 404:
            st.warning(f"OHLC data not found for this period ({status_code}).")
        else:
             st.warning(f"Could not fetch OHLC data (HTTP Error {status_code}).")
        return pd.DataFrame(columns=['timestamp', 'date', 'open', 'high', 'low', 'close'])
    except requests.exceptions.RequestException as e:
        st.warning(f"Error fetching OHLC data: {e}")
        return pd.DataFrame(columns=['timestamp', 'date', 'open', 'high', 'low', 'close'])
    except Exception as e:
        st.error(f"An error occurred processing OHLC data: {e}")
        return pd.DataFrame(columns=['timestamp', 'date', 'open', 'high', 'low', 'close'])

# --- Sidebar ---
st.sidebar.header("⚙️ Coin Selection")
coin_map = get_coin_list()

selected_coin_id = None
selected_coin_name = None

if coin_map:
    # Get all coin names, title-cased and sorted for display
    all_coin_names = sorted([name.title() for name in coin_map.keys()])
    default_coin_display_name = "Bitcoin"
    
    try:
        default_index = all_coin_names.index(default_coin_display_name)
    except ValueError:
        default_index = 0 # Default to the first coin if Bitcoin isn't found
        st.sidebar.warning("Could not find 'Bitcoin' in the coin list, defaulting to the first entry.")
        
    # Use a single selectbox with all coin names
    selected_coin_name = st.sidebar.selectbox(
        "Select Coin (Type to search)", 
        options=all_coin_names, 
        index=default_index,
        key="detail_coin_select_all"
    )
    
    if selected_coin_name:
        # Get the ID from the original map using the lowercase version of the selected name
        selected_coin_id = coin_map.get(selected_coin_name.lower())
    else:
        selected_coin_id = None # Should not happen with selectbox unless list is empty
        
    # Currency selection for market data
    currency = st.sidebar.selectbox(
        "Select Currency", 
        ["usd", "eur", "gbp", "jpy", "btc", "eth"], # Added crypto pairs
        key="detail_currency"
    )
    currency_upper = currency.upper()

else:
    st.sidebar.error("Could not load coin list from API.")
    currency = "usd"
    currency_upper = "USD"

# --- Main Page ---

if selected_coin_id and selected_coin_name:
    details = get_coin_details(selected_coin_id)

    if details:
        # --- Header (Remains outside tabs) ---
        col_h1, col_h2 = st.columns([0.1, 0.9])
        with col_h1:
            st.image(details.get('image', {}).get('large', ''), width=80)
        with col_h2:
            st.title(f"{details.get('name', 'N/A')} ({details.get('symbol', '').upper()})")
            st.caption(f"Rank #{details.get('market_cap_rank', 'N/A')}")

        st.divider()

        # --- Create Tabs --- 
        tab1, tab2, tab3 = st.tabs(["📊 Market Overview", "📈 Charts", "ℹ️ Info & Links"])

        # --- Tab 1: Market Overview ---
        with tab1:
            st.subheader("Key Market Data")
            market_data = details.get('market_data', {})
            
            # Use selected currency
            price = market_data.get('current_price', {}).get(currency, 0)
            ath = market_data.get('ath', {}).get(currency, 0)
            ath_change = market_data.get('ath_change_percentage', {}).get(currency, 0)
            ath_date_str = market_data.get('ath_date', {}).get(currency, '')
            atl = market_data.get('atl', {}).get(currency, 0)
            atl_change = market_data.get('atl_change_percentage', {}).get(currency, 0)
            atl_date_str = market_data.get('atl_date', {}).get(currency, '')
            mcap = market_data.get('market_cap', {}).get(currency, 0)
            vol = market_data.get('total_volume', {}).get(currency, 0)
            high_24h = market_data.get('high_24h', {}).get(currency, 0)
            low_24h = market_data.get('low_24h', {}).get(currency, 0)
            price_change_24h = market_data.get('price_change_percentage_24h_in_currency', {}).get(currency, 0)
            
            # Safely format dates
            try:
                ath_date = pd.to_datetime(ath_date_str).strftime('%Y-%m-%d') if ath_date_str else 'N/A'
            except: ath_date = 'N/A'
            try:
                atl_date = pd.to_datetime(atl_date_str).strftime('%Y-%m-%d') if atl_date_str else 'N/A'
            except: atl_date = 'N/A'

            # Display metrics
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric(f"Price ({currency_upper})", f"{price:,.4f}", f"{price_change_24h:.2f}% (24h)")
            m_col2.metric(f"Market Cap ({currency_upper})", f"{mcap:,.0f}")
            m_col3.metric(f"24h Volume ({currency_upper})", f"{vol:,.0f}")
            m_col4.metric(f"24h High/Low ({currency_upper})", f"{high_24h:,.2f} / {low_24h:,.2f}")
            m_col1a, m_col2a = st.columns(2)
            with m_col1a:
                 st.metric(f"All-Time High ({currency_upper})", f"{ath:,.2f} ({ath_date})", f"{ath_change:.2f}%")
            with m_col2a:
                 st.metric(f"All-Time Low ({currency_upper})", f"{atl:,.2f} ({atl_date})", f"{atl_change:.2f}%")
            
            st.divider()

            # Recent Performance
            st.subheader("Recent Price Performance")
            perf_cols = st.columns(5)
            perf_data = {
                '1h': market_data.get('price_change_percentage_1h_in_currency', {}).get(currency, None),
                '24h': market_data.get('price_change_percentage_24h_in_currency', {}).get(currency, None),
                '7d': market_data.get('price_change_percentage_7d_in_currency', {}).get(currency, None),
                '14d': market_data.get('price_change_percentage_14d_in_currency', {}).get(currency, None),
                '30d': market_data.get('price_change_percentage_30d_in_currency', {}).get(currency, None)
            }
            perf_labels = {'1h':'1 Hour', '24h':'24 Hours', '7d':'7 Days', '14d':'14 Days', '30d':'30 Days'}
            i = 0
            for period, value in perf_data.items():
                if value is not None:
                    perf_cols[i].metric(label=perf_labels[period], value=f"{value:.2f}%")
                else:
                     perf_cols[i].metric(label=perf_labels[period], value="N/A")
                i += 1
                if i >= len(perf_cols): break

            st.divider()
            
            # Supply Info
            st.subheader("Supply Information")
            circ_supply = market_data.get('circulating_supply', None)
            total_supply = market_data.get('total_supply', None)
            max_supply = market_data.get('max_supply', None)
            supply_cols = st.columns(2)
            supply_cols[0].metric("Circulating Supply", f"{circ_supply:,.0f}" if circ_supply is not None else "N/A")
            supply_cols[0].metric("Total Supply", f"{total_supply:,.0f}" if total_supply is not None else "N/A")
            supply_cols[0].metric("Max Supply", f"{max_supply:,.0f}" if max_supply is not None else "N/A")
            if circ_supply is not None and (total_supply is not None or max_supply is not None):
                supply_limit = max_supply if max_supply is not None and max_supply > 0 else total_supply
                if supply_limit is not None and supply_limit > 0:
                    remaining_supply = supply_limit - circ_supply
                    labels = ['Circulating', 'Not Circulating']
                    values = [circ_supply, remaining_supply if remaining_supply > 0 else 0]
                    fig_supply = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, 
                                                       marker_colors=['#1f77b4', 'lightgrey'], pull=[0, 0.05])])
                    fig_supply.update_layout(title_text=f'Supply Distribution (vs. {"Max" if max_supply else "Total"} Supply)',
                                            annotations=[dict(text='Supply', x=0.5, y=0.5, font_size=16, showarrow=False)],
                                            showlegend=True, height=300, margin=dict(l=10, r=10, t=50, b=10))
                    supply_cols[1].plotly_chart(fig_supply, use_container_width=True)
                else: supply_cols[1].info("Cannot generate supply chart (No valid Total/Max supply).")
            else: supply_cols[1].info("Not enough supply data to generate chart.")

        # --- Tab 2: Charts ---
        with tab2:
            # 7-Day Sparkline
            st.subheader("7-Day Price Trend (Sparkline)")
            sparkline_data = market_data.get('sparkline_7d', {}).get('price')
            if sparkline_data:
                spark_df = pd.DataFrame({'price': sparkline_data})
                spark_df['time'] = pd.to_datetime(range(len(sparkline_data)), unit='h', origin=pd.Timestamp.now() - pd.Timedelta(days=7))
                fig_spark = px.line(spark_df, x='time', y='price', title=f"{details.get('name', 'N/A')} 7d Sparkline")
                fig_spark.update_layout(xaxis_title=None, yaxis_title=None, showlegend=False)
                st.plotly_chart(fig_spark, use_container_width=True)
            else: st.info("7-day sparkline data not available.")

            st.divider()

            # Historical Chart Section
            st.subheader("Historical Price & Volume")
            chart_type = st.radio("Select Chart Type", ["Line Chart", "Candlestick Chart"], key="detail_chart_type", horizontal=True)
            days_history_detail = st.selectbox("Select Timeframe (Days)", options=[7, 30, 90, 365], index=1, key="detail_days_history")
            
            # Fetch appropriate data (OHLC for candlestick, Price/Volume for Line)
            if chart_type == "Line Chart":
                hist_data = get_historical_data(selected_coin_id, currency, days=str(days_history_detail))
            else: # Candlestick Chart
                hist_data = get_ohlc_data(selected_coin_id, currency, days=str(days_history_detail))
                # Also fetch volume data separately for candlestick as OHLC endpoint doesn't include it
                volume_data = get_historical_data(selected_coin_id, currency, days=str(days_history_detail))[['date', 'volume']]
                if not volume_data.empty:
                    # Merge volume into hist_data for consistent access
                    hist_data = pd.merge(hist_data, volume_data, on='date', how='left')

            if not hist_data.empty:
                # Create figure with secondary y-axis for volume
                fig_hist = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Add Price Trace (Line or Candlestick)
                if chart_type == "Line Chart":
                    fig_hist.add_trace(go.Scatter(x=hist_data["date"], y=hist_data["price"], name=f"Price ({currency_upper})", line=dict(color='blue')), secondary_y=False)
                else: # Candlestick
                    fig_hist.add_trace(go.Candlestick(x=hist_data['date'], open=hist_data['open'], high=hist_data['high'], low=hist_data['low'], close=hist_data['close'], name='Price (OHLC)'), secondary_y=False)
                    fig_hist.update_layout(xaxis_rangeslider_visible=False)
                
                # Add Volume Trace (Bar Chart on secondary axis)
                if 'volume' in hist_data.columns and not hist_data['volume'].isnull().all():
                    fig_hist.add_trace(go.Bar(x=hist_data["date"], y=hist_data["volume"], name=f"Volume ({currency_upper})", marker_color='rgba(128,128,128,0.5)'), secondary_y=True)
                    fig_hist.update_yaxes(title_text=f"Volume ({currency_upper})", secondary_y=True, showgrid=False)
                
                # Update layout
                fig_hist.update_layout(
                    title_text=f"{details.get('name', 'N/A')} Price & Volume ({days_history_detail} Days)",
                    xaxis_title='Date'
                )
                fig_hist.update_yaxes(title_text=f"Price ({currency_upper})", secondary_y=False)
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.warning(f"Could not display historical data for {details.get('name', 'N/A')}.")

        # --- Tab 3: Info & Links ---
        with tab3:
            # Description
            st.subheader("About")
            description = details.get('description', {}).get('en', 'No description available.')
            with st.expander("Read Description...", expanded=False):
                import re
                clean_desc = re.sub('<[^<]+?>', '', description) if description else 'No description available.'
                st.markdown(clean_desc)

            st.divider()

            # Links
            st.subheader("Official Links")
            links = details.get('links', {})
            homepage = links.get('homepage', [])[0] if links.get('homepage') else None
            blockchain_explorers = links.get('blockchain_site', [])[:3]
            twitter = links.get('twitter_screen_name', None)
            subreddit = links.get('subreddit_url', None)
            link_cols = st.columns(4)
            if homepage: link_cols[0].link_button("Homepage", homepage)
            if twitter: link_cols[1].link_button("Twitter", f"https://twitter.com/{twitter}")
            if subreddit: link_cols[2].link_button("Reddit", subreddit)
            if blockchain_explorers:
                 with st.expander("Blockchain Explorers"):
                     for i, explorer in enumerate(blockchain_explorers):
                         if explorer: st.link_button(f"Explorer {i+1}", explorer)

    else:
        st.error(f"Could not retrieve details for the selected coin ID: {selected_coin_id}")

elif not coin_map:
     st.error("Application cannot function without the coin list. Please check API status.")
elif selected_coin_id is None and selected_coin_name:
    # Handle case where selected name didn't map to an ID (should be rare)
    st.error(f"Could not find ID for selected coin: {selected_coin_name}")
else:
    st.info("⬅️ Please select a coin from the sidebar to view its details.") 