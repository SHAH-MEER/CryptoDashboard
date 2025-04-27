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
import utils # Import the utility module
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
# Functions moved to utils.py:
# get_coin_list()
# get_historical_data(coin_id, currency, days)

# --- Sidebar --- 
st.sidebar.header("⚙️ Analysis Options")
# Call function from utils module
coin_map = utils.get_coin_list()

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
        if all_coin_names: # Check if list is not empty
             st.sidebar.warning(f"Could not find '{default_coin_display_name}', defaulting to '{all_coin_names[0]}'.")
        else:
             st.sidebar.error("Coin list empty.")

    # Use a single selectbox with all coin names
    selected_coin_name = st.sidebar.selectbox(
        "Select Coin (Type to search)", 
        options=all_coin_names, 
        index=default_index if all_coin_names else None,
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
        index=2, # Default to 90 days
        key="tsa_days_history"
    )
    
    # Moving average options
    st.sidebar.markdown("**Moving Averages**")
    ma_type = st.sidebar.radio("MA Type", ("SMA", "EMA"), key="tsa_ma_type")
    ma_short_window = st.sidebar.number_input(f"Short-term {ma_type} Window (days)", min_value=1, max_value=50, value=7, step=1, key="ma_short")
    ma_long_window = st.sidebar.number_input(f"Long-term {ma_type} Window (days)", min_value=10, max_value=200, value=30, step=1, key="ma_long")
    
    # Volatility options
    st.sidebar.markdown("**Volatility**")
    volatility_window = st.sidebar.number_input("Rolling Volatility Window (days)", min_value=5, max_value=100, value=30, step=1, key="tsa_vol_window")
    
    # Autocorrelation options
    st.sidebar.markdown("**Autocorrelation**")
    acf_pacf_target = st.sidebar.radio("ACF/PACF On", ("Daily Returns", "Price"), key="tsa_acf_target")
    acf_pacf_lags = st.sidebar.slider("Max Lags for ACF/PACF", min_value=10, max_value=100, value=40, key="tsa_acf_lags")

else:
    st.sidebar.error("Could not load coin list from API.")
    currency = "usd"
    currency_upper = "USD"
    days_history = 90
    ma_type = "SMA"
    ma_short_window = 7
    ma_long_window = 30
    volatility_window = 30
    acf_pacf_target = "Daily Returns"
    acf_pacf_lags = 40

# --- Main Page ---
if selected_coin_id and selected_coin_name:
    st.header(f"Analysis for: {selected_coin_name} ({currency_upper}) - Last {days_history} Days")
    
    # Fetch data using utils module
    hist_df_raw = utils.get_historical_data(selected_coin_id, currency, days=days_history)

    if not hist_df_raw.empty and 'price' in hist_df_raw.columns:
        # Set date as index for time series operations
        hist_df = hist_df_raw.set_index('date')
        hist_df = hist_df[['price']] # Start with price column
        
        # --- Calculations ---
        # Moving Averages
        if ma_type == "SMA":
            hist_df[f'MA_{ma_short_window}'] = hist_df['price'].rolling(window=ma_short_window).mean()
            hist_df[f'MA_{ma_long_window}'] = hist_df['price'].rolling(window=ma_long_window).mean()
        else: # EMA
            hist_df[f'MA_{ma_short_window}'] = hist_df['price'].ewm(span=ma_short_window, adjust=False).mean()
            hist_df[f'MA_{ma_long_window}'] = hist_df['price'].ewm(span=ma_long_window, adjust=False).mean()
            
        # Daily Returns
        hist_df['Daily Return'] = hist_df['price'].pct_change() * 100
        
        # Rolling Volatility (Standard Deviation of Daily Returns)
        hist_df['Volatility'] = hist_df['Daily Return'].rolling(window=volatility_window).std()
        
        # Drop initial NaNs created by calculations
        hist_df_analysis = hist_df.dropna() 

        # --- Create Tabs for Analysis Sections ---
        tab1, tab2, tab3, tab4 = st.tabs([
            f"📈 Price & {ma_type}", 
            "📊 Returns & Volatility", 
            "📉 Decomposition",
            "🔗 Autocorrelation (ACF/PACF)"
        ])

        # --- Tab 1: Price and Moving Averages ---
        with tab1:
            st.markdown(f"**Price and {ma_type} ({ma_short_window}-day & {ma_long_window}-day)**")
            
            fig_price_ma = go.Figure()
            # Add Price trace
            fig_price_ma.add_trace(go.Scatter(x=hist_df_analysis.index, y=hist_df_analysis['price'], mode='lines', name=f"Price ({currency_upper})"))
            # Add Short MA trace
            fig_price_ma.add_trace(go.Scatter(x=hist_df_analysis.index, y=hist_df_analysis[f'MA_{ma_short_window}'], mode='lines', name=f'{ma_type}-{ma_short_window}d'))
            # Add Long MA trace
            fig_price_ma.add_trace(go.Scatter(x=hist_df_analysis.index, y=hist_df_analysis[f'MA_{ma_long_window}'], mode='lines', name=f'{ma_type}-{ma_long_window}d'))
            
            fig_price_ma.update_layout(title=f"{selected_coin_name} Price & Moving Averages", 
                                     xaxis_title="Date", yaxis_title=f"Price ({currency_upper})",
                                     legend_title="Metric")
            st.plotly_chart(fig_price_ma, use_container_width=True)
            
            # Display raw data if checkbox is selected
            if st.checkbox("Show Price/MA Data Table", key="tsa_show_price_data"): 
                 st.dataframe(hist_df_analysis[['price', f'MA_{ma_short_window}', f'MA_{ma_long_window}']].style.format("{:,.4f}"))

        # --- Tab 2: Returns Analysis ---
        with tab2:
            st.markdown("**Daily Returns and Rolling Volatility**")
            col_ret1, col_ret2 = st.columns(2)
            with col_ret1:
                st.markdown("**Daily Returns (%)**")
                fig_returns = px.line(hist_df_analysis, y='Daily Return', title="Daily Returns")
                fig_returns.update_layout(yaxis_title="Return (%)", showlegend=False, height=300)
                st.plotly_chart(fig_returns, use_container_width=True)
                
                st.markdown(f"**Rolling Volatility ({volatility_window}-day Std Dev)**")
                fig_volatility = px.line(hist_df_analysis, y='Volatility', title="Rolling Volatility")
                fig_volatility.update_layout(yaxis_title="Std Dev (%)", showlegend=False, height=300)
                st.plotly_chart(fig_volatility, use_container_width=True)
                
            with col_ret2:
                st.markdown("**Distribution of Daily Returns**")
                fig_hist_returns = px.histogram(hist_df_analysis, x='Daily Return', nbins=50, title="Histogram of Daily Returns")
                fig_hist_returns.update_layout(xaxis_title="Return (%)", yaxis_title="Frequency", height=300)
                st.plotly_chart(fig_hist_returns, use_container_width=True)
                
                st.markdown("**Return Statistics**")
                st.dataframe(hist_df_analysis['Daily Return'].describe().to_frame().style.format("{:.3f}%"))
                
            if st.checkbox("Show Returns/Volatility Data Table", key="tsa_show_return_data"): 
                st.dataframe(hist_df_analysis[['Daily Return', 'Volatility']].style.format('{{:.3f}}'))

        # --- Tab 3: Decomposition ---
        with tab3:
             st.markdown("**Time Series Decomposition (Additive Model)**")
             try:
                 # Ensure we have enough data points (>= 2 * period)
                 # Using a common default period (e.g., 7 for weekly seasonality, if applicable)
                 period = 7 if len(hist_df_analysis) >= 14 else (len(hist_df_analysis) // 2 if len(hist_df_analysis) >= 4 else 2)
                 if len(hist_df_analysis) < 4:
                      st.warning("Not enough data points (< 4) for decomposition.")
                 else:
                      decomposition = seasonal_decompose(hist_df_analysis['price'], model='additive', period=period) # Using 7-day period common for financial data
                      
                      fig_decomp = go.Figure()
                      fig_decomp.add_trace(go.Scatter(x=decomposition.trend.index, y=decomposition.trend, mode='lines', name='Trend'))
                      fig_decomp.add_trace(go.Scatter(x=decomposition.seasonal.index, y=decomposition.seasonal, mode='lines', name='Seasonality'))
                      fig_decomp.add_trace(go.Scatter(x=decomposition.resid.index, y=decomposition.resid, mode='lines', name='Residual'))
                      
                      fig_decomp.update_layout(title=f"Price Decomposition (Period={period})", xaxis_title="Date", yaxis_title="Component Value", height=500)
                      st.plotly_chart(fig_decomp, use_container_width=True)
                      
                      if st.checkbox("Show Decomposition Data Table", key="tsa_show_decomp_data"): 
                          decomp_df = pd.concat([decomposition.trend, decomposition.seasonal, decomposition.resid], axis=1)
                          decomp_df.columns = ['Trend', 'Seasonal', 'Residual']
                          st.dataframe(decomp_df.style.format("{:,.4f}"))
                          
             except ValueError as e:
                  st.warning(f"Could not perform seasonal decomposition: {e}. Try adjusting the timeframe or coin.")
             except Exception as e:
                  st.error(f"An unexpected error occurred during decomposition: {e}")
                  
        # --- Tab 4: Autocorrelation (ACF/PACF) ---
        with tab4:
             st.markdown("**Autocorrelation Function (ACF) and Partial Autocorrelation Function (PACF)**")
             st.markdown(f"Plotting ACF/PACF for **{acf_pacf_target}** with max lags = {acf_pacf_lags}")
             
             target_series = None
             series_name = ""
             
             if acf_pacf_target == "Daily Returns":
                 target_series = hist_df_analysis['Daily Return'].dropna()
                 series_name = "Daily Returns"
             else: # Price
                 # Check for stationarity using ADF test before plotting ACF/PACF on price
                 adf_result = adfuller(hist_df_analysis['price'].dropna())
                 st.write(f"**Augmented Dickey-Fuller Test (ADF) for Price Stationarity:**")
                 st.write(f"ADF Statistic: {adf_result[0]:.4f}")
                 st.write(f"p-value: {adf_result[1]:.4f}")
                 if adf_result[1] > 0.05:
                     st.warning("Price series appears non-stationary (p-value > 0.05). ACF/PACF plots on differenced price might be more informative. Calculating first difference...")
                     target_series = hist_df_analysis['price'].diff().dropna()
                     series_name = "Differenced Price"
                 else:
                     st.success("Price series appears stationary (p-value <= 0.05). Plotting ACF/PACF on original price.")
                     target_series = hist_df_analysis['price'].dropna()
                     series_name = "Price"
             
             if target_series is not None and not target_series.empty:
                 try:
                     # Plot ACF and PACF using matplotlib within Streamlit
                     fig_acf_pacf, axes = plt.subplots(1, 2, figsize=(12, 4))
                     plot_acf(target_series, lags=acf_pacf_lags, ax=axes[0], title=f'ACF ({series_name})')
                     plot_pacf(target_series, lags=acf_pacf_lags, ax=axes[1], title=f'PACF ({series_name})')
                     plt.tight_layout()
                     st.pyplot(fig_acf_pacf)
                     plt.close(fig_acf_pacf) # Close the plot to free memory
                 except Exception as e:
                     st.error(f"Error plotting ACF/PACF: {e}")
             elif target_series is not None and target_series.empty:
                  st.warning(f"Not enough data points remaining after processing for {series_name} to plot ACF/PACF.")
             else: # Should not happen based on logic above, but as a fallback
                  st.warning("Target series for ACF/PACF is empty or undefined.")

    elif not hist_df_raw.empty and 'price' not in hist_df_raw.columns:
         st.warning("Historical data fetched, but 'price' column is missing.")
    else:
        st.warning("Could not fetch or process historical data for the selected coin and timeframe. Check API status or try again later.")

elif not coin_map:
     st.error("Application cannot function without the coin list. Please check API status.")
elif selected_coin_id is None and selected_coin_name:
    st.error(f"Could not find ID for selected coin: {selected_coin_name}")
else:
    st.info("⬅️ Please select a coin and options from the sidebar to start the analysis.") 