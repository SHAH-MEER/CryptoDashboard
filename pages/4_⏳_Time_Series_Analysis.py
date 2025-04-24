import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.seasonal import seasonal_decompose
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

# --- ADF Test Function ---
def run_adf_test(series):
    result = adfuller(series.dropna()) # Drop NaNs before testing
    p_value = result[1]
    is_stationary = p_value < 0.05
    return is_stationary, p_value

st.set_page_config(page_title="Time Series Analysis", page_icon="⏳", layout="wide")

st.title("⏳ Time Series Analysis")

# --- Helper Functions (Copied from Coin Detail - consider refactoring to utils.py later) ---

@st.cache_data(ttl=3600 * 6)
def get_coin_list():
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {coin['name'].lower(): coin['id'] for coin in data}
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching coin list: {e}")
        return {}
    except Exception as e:
        st.error(f"An error occurred processing the coin list: {e}")
        return {}

@st.cache_data(ttl=7200)
def get_historical_data(coin_id, currency, days):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={currency}&days={days}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        prices = data["prices"]
        # Also fetch market caps and total volumes if needed later, TBD
        # market_caps = data.get("market_caps", [])
        # total_volumes = data.get("total_volumes", [])
        df_hist = pd.DataFrame(prices, columns=["timestamp", "price"])
        df_hist["date"] = pd.to_datetime(df_hist["timestamp"], unit="ms")
        df_hist = df_hist.set_index('date') # Set date as index for time series operations
        df_hist = df_hist[['price']] # Keep only price for now
        return df_hist
    except requests.exceptions.HTTPError as http_err:
        status_code = response.status_code
        if status_code == 429:
             st.warning(f"Rate limit hit fetching historical data. Please wait.")
        elif status_code == 401:
             st.error(f"Error 401: Unauthorized. Fetching 'max' historical data may require a paid API key.")
        elif status_code == 404:
            st.warning(f"Historical data not found for this period ({status_code}).")
        else:
             st.warning(f"Could not fetch historical data (HTTP Error {status_code}).")
        return pd.DataFrame(columns=["price"])
    except requests.exceptions.RequestException as e:
        st.warning(f"Error fetching historical data: {e}")
        return pd.DataFrame(columns=["price"])
    except KeyError: # Handle cases where 'prices' key might be missing
        st.warning("Historical price data format unexpected or missing.")
        return pd.DataFrame(columns=["price"])


# --- Sidebar --- 
st.sidebar.header("⚙️ Analysis Options")
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
        default_index = 0 
        st.sidebar.warning("Could not find 'Bitcoin' in the coin list, defaulting to the first entry.")

    # Use a single selectbox with all coin names
    selected_coin_name = st.sidebar.selectbox(
        "Select Coin (Type to search)", 
        options=all_coin_names, 
        index=default_index,
        key="tsa_coin_select_all"
    )
    
    if selected_coin_name:
        # Get the ID from the original map using the lowercase version of the selected name
        selected_coin_id = coin_map.get(selected_coin_name.lower())
    else:
        selected_coin_id = None
        
    currency = st.sidebar.selectbox(
        "Select Currency", 
        ["usd", "eur", "gbp", "jpy", "btc", "eth"], 
        key="tsa_currency"
    )
    currency_upper = currency.upper()
    
    days_history = st.sidebar.selectbox(
        "Select Timeframe (Days)", 
        options=[30, 90, 180, 365], 
        index=1, # Default to 90 days
        key="tsa_days_history"
    )
    
    # Rolling window options
    st.sidebar.markdown("**Moving Averages**")
    sma_short_window = st.sidebar.number_input("Short-term SMA Window (days)", min_value=1, max_value=50, value=7, step=1, key="sma_short")
    sma_long_window = st.sidebar.number_input("Long-term SMA Window (days)", min_value=10, max_value=200, value=30, step=1, key="sma_long")

else:
    st.sidebar.error("Could not load coin list from API.")
    currency = "usd"
    currency_upper = "USD"

# --- Main Page ---
if selected_coin_id and selected_coin_name:
    st.header(f"Analysis for {selected_coin_name} ({currency_upper})")
    
    hist_df = get_historical_data(selected_coin_id, currency, days=str(days_history))
    
    if not hist_df.empty:
        
        # Check if enough data for decomposition (e.g., need at least 2 cycles for yearly)
        # Assuming daily data, let's require at least 14 days for weekly decomp
        min_decomp_len = 14 
        can_decompose = len(hist_df) >= min_decomp_len
        
        # Use Tabs for organization
        tab1, tab2, tab3 = st.tabs(["📈 Price & Moving Averages", "📊 Returns Analysis", "📉 Decomposition & Autocorrelation"])
        
        # --- Tab 1: Price & Moving Averages --- 
        with tab1:
            # Add EMA calculation option
            st.markdown("**Moving Average Options**")
            ma_type = st.radio("Select Moving Average Type", ["SMA", "EMA"], key="tsa_ma_type", horizontal=True)
            # SMA windows are already defined in sidebar
            ema_short_window = sma_short_window # Reuse sidebar values for consistency
            ema_long_window = sma_long_window
            
            # Calculate Moving Averages
            ma_calculated = False
            if ma_type == "SMA":
                if sma_short_window < len(hist_df) and sma_long_window < len(hist_df):
                    hist_df[f'SMA_{sma_short_window}'] = hist_df['price'].rolling(window=sma_short_window).mean()
                    hist_df[f'SMA_{sma_long_window}'] = hist_df['price'].rolling(window=sma_long_window).mean()
                    ma_calculated = True
                else: st.warning("Selected SMA window(s) larger than timeframe.")
            else: # EMA
                if ema_short_window < len(hist_df) and ema_long_window < len(hist_df):
                    hist_df[f'EMA_{ema_short_window}'] = hist_df['price'].ewm(span=ema_short_window, adjust=False).mean()
                    hist_df[f'EMA_{ema_long_window}'] = hist_df['price'].ewm(span=ema_long_window, adjust=False).mean()
                    ma_calculated = True
                else: st.warning("Selected EMA window(s) larger than timeframe.")

            st.subheader(f"Price and {ma_type}s")
            fig_price_ma = go.Figure()
            fig_price_ma.add_trace(go.Scatter(x=hist_df.index, y=hist_df['price'], mode='lines', name='Price', line=dict(color='blue')))
            if ma_calculated:
                if ma_type == "SMA":
                    short_label, long_label = f'SMA_{sma_short_window}', f'SMA_{sma_long_window}'
                else:
                     short_label, long_label = f'EMA_{ema_short_window}', f'EMA_{ema_long_window}'
                if short_label in hist_df.columns: fig_price_ma.add_trace(go.Scatter(x=hist_df.index, y=hist_df[short_label], mode='lines', name=f'{ma_type} {ema_short_window}d', line=dict(color='orange')))
                if long_label in hist_df.columns: fig_price_ma.add_trace(go.Scatter(x=hist_df.index, y=hist_df[long_label], mode='lines', name=f'{ma_type} {ema_long_window}d', line=dict(color='green')))
            
            fig_price_ma.update_layout(title=f'{selected_coin_name} Price & {ma_type}s ({days_history} Days)',
                                        xaxis_title='Date', yaxis_title=f'Price ({currency_upper})', legend_title="Metric")
            st.plotly_chart(fig_price_ma, use_container_width=True)
        
        # --- Tab 2: Returns Analysis --- 
        with tab2:
            # Calculate Daily Returns
            hist_df['Daily Return'] = hist_df['price'].pct_change() * 100
            
            st.subheader("Daily Percentage Returns")
            fig_returns = go.Figure()
            fig_returns.add_trace(go.Scatter(x=hist_df.index, y=hist_df['Daily Return'], mode='lines', name='Daily Return', line=dict(color='purple')))
            fig_returns.add_hline(y=0, line_width=1, line_dash="dash", line_color="red")
            fig_returns.update_layout(title=f'{selected_coin_name} Daily Returns (%) ({days_history} Days)',
                                         xaxis_title='Date', yaxis_title='Return (%)', showlegend=False)
            st.plotly_chart(fig_returns, use_container_width=True)
            
            st.subheader("Return Statistics")
            avg_return = hist_df['Daily Return'].mean()
            std_return = hist_df['Daily Return'].std()
            col1, col2 = st.columns(2)
            col1.metric("Average Daily Return", f"{avg_return:.3f}%")
            col2.metric("Std Dev of Daily Return (Volatility)", f"{std_return:.3f}%")

            st.divider()
            
            st.subheader("Distribution of Daily Returns")
            fig_hist = px.histogram(hist_df, x="Daily Return", nbins=50,
                                    title=f"{selected_coin_name} Distribution of Daily Returns ({days_history} Days)")
            fig_hist.update_layout(xaxis_title="Daily Return (%)", yaxis_title="Frequency")
            st.plotly_chart(fig_hist, use_container_width=True)

            st.divider()

            st.subheader("Rolling Volatility (30-Day Standard Deviation of Daily Returns)")
            rolling_window = 30
            if len(hist_df) > rolling_window:
                hist_df['Volatility'] = hist_df['Daily Return'].rolling(window=rolling_window).std() * (365**0.5)
                fig_vol = px.line(hist_df.dropna(), y='Volatility', 
                                  title=f"{selected_coin_name} {rolling_window}-Day Rolling Volatility ({days_history} Days)")
                fig_vol.update_layout(xaxis_title="Date", yaxis_title="Annualized Volatility" if 'Annualized' in fig_vol.layout.yaxis.title.text else "30d Rolling Std Dev (%)")
                st.plotly_chart(fig_vol, use_container_width=True)
            else:
                st.info(f"Not enough data ({len(hist_df)} days) for {rolling_window}-day rolling volatility calculation.")
        
        # --- Tab 3: Decomposition & Autocorrelation --- 
        with tab3:
            st.subheader("Seasonal Decomposition")
            st.info("Decomposes the price series into Trend, Seasonal, and Residual components. Assumes an additive model and daily data (period=7 for weekly seasonality).")
            
            if can_decompose:
                try:
                    # Perform decomposition (using period=7 for weekly patterns in daily data)
                    decomposition = seasonal_decompose(hist_df['price'], model='additive', period=7) 
                    
                    # Create Plotly figure for decomposition
                    fig_decomp = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                                               subplot_titles=("Observed", "Trend", "Seasonal", "Residual"))

                    fig_decomp.add_trace(go.Scatter(x=decomposition.observed.index, y=decomposition.observed, mode='lines', name='Observed'), row=1, col=1)
                    fig_decomp.add_trace(go.Scatter(x=decomposition.trend.index, y=decomposition.trend, mode='lines', name='Trend'), row=2, col=1)
                    fig_decomp.add_trace(go.Scatter(x=decomposition.seasonal.index, y=decomposition.seasonal, mode='lines', name='Seasonal'), row=3, col=1)
                    fig_decomp.add_trace(go.Scatter(x=decomposition.resid.index, y=decomposition.resid, mode='markers', name='Residual', marker=dict(size=3)), row=4, col=1)

                    fig_decomp.update_layout(height=700, title_text=f"{selected_coin_name} Time Series Decomposition", showlegend=False)
                    st.plotly_chart(fig_decomp, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not perform seasonal decomposition: {e}")
                    st.error("This might happen if the time series has too few observations or no clear seasonality.")
            else:
                st.warning(f"Not enough data ({len(hist_df)} points) for seasonal decomposition (requires at least {min_decomp_len} points).")
                
            st.divider()
            st.subheader("Autocorrelation Analysis")
            # Calculate log returns for ACF/PACF
            returns = np.log(hist_df['price'] / hist_df['price'].shift(1)).dropna() * 100
            
            acf_pacf_target = st.radio("Select Series for ACF/PACF", ["Daily Returns", "Price"], key="acf_target", horizontal=True)
            
            if acf_pacf_target == "Daily Returns":
                 target_series = returns
                 title_suffix = "of Daily Log Returns"
            else: # Price
                 # Check stationarity of price first
                 is_stationary_price, p_val_price = run_adf_test(hist_df['price'])
                 if not is_stationary_price:
                     st.info("Price series is non-stationary. Displaying ACF/PACF on first difference.")
                     target_series = hist_df['price'].diff().dropna()
                     title_suffix = "of Differenced Price"
                 else:
                     st.info("Price series appears stationary. Displaying ACF/PACF on original price.")
                     target_series = hist_df['price']
                     title_suffix = "of Price"
            
            if target_series.empty or len(target_series) < 20:
                st.warning(f"Not enough data ({len(target_series)} points) for autocorrelation analysis on {acf_pacf_target}.")
            else:
                max_lags = min(40, len(target_series) // 2 - 1)
                if max_lags < 1:
                     st.warning("Not enough data points to calculate meaningful lags.")
                else:
                    st.markdown("**Autocorrelation Function (ACF)**")
                    fig_acf, ax_acf = plt.subplots(figsize=(10, 4))
                    plot_acf(target_series, lags=max_lags, ax=ax_acf, zero=False)
                    ax_acf.set_title(f'ACF {title_suffix}')
                    ax_acf.set_xlabel('Lag'); ax_acf.set_ylabel('Autocorrelation')
                    st.pyplot(fig_acf)
                    plt.close(fig_acf)

                    st.markdown("**Partial Autocorrelation Function (PACF)**")
                    fig_pacf, ax_pacf = plt.subplots(figsize=(10, 4))
                    plot_pacf(target_series, lags=max_lags, ax=ax_pacf, zero=False, method='ols')
                    ax_pacf.set_title(f'PACF {title_suffix}')
                    ax_pacf.set_xlabel('Lag'); ax_pacf.set_ylabel('Partial Autocorrelation')
                    st.pyplot(fig_pacf)
                    plt.close(fig_pacf)

        # --- Optional Raw Data Table --- 
        st.divider()
        if st.checkbox("Show Raw Data with Analysis", key="tsa_show_data"): 
            st.subheader("Data Table")
            # Add Volatility to format if it exists
            format_dict = {
                'price': '{:,.4f}'.format,
                'Daily Return': '{:.3f}%'.format
            }
            if f'SMA_{sma_short_window}' in hist_df.columns: format_dict[f'SMA_{sma_short_window}'] = '{:,.4f}'.format
            if f'SMA_{sma_long_window}' in hist_df.columns: format_dict[f'SMA_{sma_long_window}'] = '{:,.4f}'.format
            if 'Volatility' in hist_df.columns: format_dict['Volatility'] = '{:.3f}'.format
            st.dataframe(hist_df.style.format(format_dict)) # Use updated format dict

    else:
        st.warning("Could not fetch or process historical data for the selected coin and timeframe.")

elif not coin_map:
     st.error("Application cannot function without the coin list. Please check API status.")
elif selected_coin_id is None and selected_coin_name:
    st.error(f"Could not find ID for selected coin: {selected_coin_name}")
else:
    st.info("⬅️ Please select a coin from the sidebar to start the analysis.") 