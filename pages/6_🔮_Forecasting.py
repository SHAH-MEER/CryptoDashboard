import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from prophet import Prophet
from prophet.plot import plot_plotly, plot_components_plotly
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import matplotlib.pyplot as plt
import warnings
import utils # Import the utility module

st.set_page_config(page_title="Forecasting & Analysis", page_icon="🔮", layout="wide")

st.title("🔮 Time Series Forecasting & Analysis")

st.warning("**Disclaimer:** Cryptocurrency price forecasting is highly speculative and notoriously difficult. These models are for educational purposes only and should **not** be considered financial advice. Past performance is not indicative of future results.")

# --- Helper Functions (Copied - consider refactoring) ---
# Functions moved to utils.py:
# get_coin_list()
# get_historical_data(coin_id, currency, days)

# Function to perform ADF test and display results
def run_adf_test(series, series_name="Price"):
    st.write(f"**Augmented Dickey-Fuller Test for Stationarity ({series_name}):**")
    try:
        adf_result = adfuller(series.dropna())
        st.write(f"ADF Statistic: {adf_result[0]:.4f}")
        st.write(f"p-value: {adf_result[1]:.4f}")
        if adf_result[1] > 0.05:
            st.warning(f"{series_name} series appears non-stationary (p > 0.05). ARIMA models might require differencing.")
            return False, adf_result[1]
        else:
            st.success(f"{series_name} series appears stationary (p <= 0.05).")
            return True, adf_result[1]
    except Exception as e:
        st.error(f"Could not perform ADF test: {e}")
        return None, None

# --- Sidebar --- 
st.sidebar.header("⚙️ Forecasting Options")
# Call function from utils module
coin_map = utils.get_coin_list()

selected_coin_id = None
selected_coin_name = None

if coin_map:
    all_coin_names = sorted([name.title() for name in coin_map.keys()])
    default_coin_display_name = "Bitcoin"
    try:
        default_index = all_coin_names.index(default_coin_display_name)
    except ValueError:
        default_index = 0
        if all_coin_names: st.sidebar.warning(f"Default '{default_coin_display_name}' not found.")
        else: st.sidebar.error("Coin list empty.")

    selected_coin_name = st.sidebar.selectbox(
        "Select Coin (Type to search)", 
        options=all_coin_names, 
        index=default_index if all_coin_names else None,
        key="forecast_coin_select"
    )
    if selected_coin_name:
        selected_coin_id = coin_map.get(selected_coin_name.lower())
        
    currency = st.sidebar.selectbox(
        "Select Currency", 
        ["usd", "eur", "gbp", "jpy"], # Limit to fiat for simplicity first
        key="forecast_currency"
    )
    currency_upper = currency.upper()
    
    # Use a longer default period for training forecasting models
    days_history = st.sidebar.selectbox(
        "Select Historical Period for Training", 
        options=[90, 180, 365, 730], # Added 730 days (2 years)
        index=2, # Default to 365 days
        key="forecast_days_history",
        help="Amount of past data used to train the model."
    )
    
    forecast_horizon = st.sidebar.slider(
        "Select Forecast Horizon (Days)", 
        min_value=7, max_value=90, value=30, step=7, 
        key="forecast_horizon",
        help="How many days into the future to forecast."
    )
    
    # Model Specific Options
    st.sidebar.markdown("**Model Tuning (Optional)**")
    # ARIMA Order (example)
    with st.sidebar.expander("ARIMA Order (p, d, q)"):
         p_arima = st.number_input("p (AR order)", min_value=0, max_value=10, value=5, step=1, key="arima_p")
         d_arima = st.number_input("d (Differencing)", min_value=0, max_value=3, value=1, step=1, key="arima_d")
         q_arima = st.number_input("q (MA order)", min_value=0, max_value=10, value=0, step=1, key="arima_q")
         arima_order_selected = (p_arima, d_arima, q_arima)
         
    # Prophet Seasonality (example)
    with st.sidebar.expander("Prophet Components"):
         prophet_yearly = st.checkbox("Yearly Seasonality", value=True, key="prophet_yearly")
         prophet_weekly = st.checkbox("Weekly Seasonality", value=True, key="prophet_weekly")
         prophet_daily = st.checkbox("Daily Seasonality", value=False, key="prophet_daily")


else:
    st.sidebar.error("Could not load coin list from API.")
    currency = "usd"
    currency_upper = "USD"
    days_history = 365
    forecast_horizon = 30
    arima_order_selected = (5, 1, 0)
    prophet_yearly = True
    prophet_weekly = True
    prophet_daily = False

# --- Main Content --- 

if selected_coin_id and selected_coin_name:
    st.header(f"Forecasting for: {selected_coin_name} ({currency_upper})")
    st.markdown(f"Training data: Last {days_history} days. Forecasting: Next {forecast_horizon} days.")

    # --- Load and Prepare Data ---
    # Call function from utils module
    hist_df_orig = utils.get_historical_data(selected_coin_id, currency, days=days_history)

    if not hist_df_orig.empty and 'price' in hist_df_orig.columns and len(hist_df_orig) > 30: # Require minimum data points
        
        # Prepare data for Prophet (needs 'ds' and 'y')
        df_prophet = hist_df_orig.rename(columns={'date': 'ds', 'price': 'y'})[['ds', 'y']].copy()
        
        # Prepare data for ARIMA (needs date index and price column)
        df_arima = hist_df_orig.set_index('date')[['price']].copy()
        # Ensure daily frequency and fill gaps (important for ARIMA)
        df_arima = df_arima.asfreq('D').ffill().dropna()

        if df_arima.empty or df_prophet.empty:
             st.warning("Data preprocessing resulted in empty dataframe. Cannot proceed.")
        else:
             # --- Create Tabs for Models ---
             tab1, tab2, tab3 = st.tabs(["🚀 Prophet Forecast", "📈 ARIMA Forecast", "🔗 Autocorrelation Analysis"])
             
             # --- Tab 1: Prophet --- 
             with tab1:
                 st.subheader("Prophet Model Forecast")
                 with st.spinner("Training Prophet model and generating forecast..."):
                     try:
                         # Initialize and fit Prophet model
                         model_prophet = Prophet(
                             yearly_seasonality=prophet_yearly,
                             weekly_seasonality=prophet_weekly,
                             daily_seasonality=prophet_daily
                         )
                         model_prophet.fit(df_prophet)
                         
                         # Create future dataframe and make predictions
                         future = model_prophet.make_future_dataframe(periods=forecast_horizon)
                         forecast_prophet = model_prophet.predict(future)
                         
                         # Plot forecast
                         st.markdown("**Forecast Plot**")
                         fig_forecast = plot_plotly(model_prophet, forecast_prophet)
                         fig_forecast.update_layout(title=f"{selected_coin_name} Forecast (Prophet)", 
                                                xaxis_title="Date", yaxis_title=f"Price ({currency_upper})")
                         st.plotly_chart(fig_forecast, use_container_width=True)
                         
                         # Plot components
                         st.markdown("**Forecast Components**")
                         fig_components = plot_components_plotly(model_prophet, forecast_prophet)
                         st.plotly_chart(fig_components, use_container_width=True)
                         
                         if st.checkbox("Show Prophet Forecast Data", key="prophet_data"):
                             st.dataframe(forecast_prophet[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(forecast_horizon))
                             
                     except Exception as e:
                          st.error(f"Error running Prophet model: {e}")
                          st.info("Prophet often requires more data (e.g., 1-2 years) for robust seasonality detection.")
                          
             # --- Tab 2: ARIMA --- 
             with tab2:
                  st.subheader("ARIMA Model Forecast")
                  st.markdown(f"Selected Order: **p={arima_order_selected[0]}, d={arima_order_selected[1]}, q={arima_order_selected[2]}**")
                  
                  # Perform ADF test first
                  is_stationary, p_value = run_adf_test(df_arima['price'])
                  
                  with st.spinner("Training ARIMA model and generating forecast..."):
                      try:
                           # Fit ARIMA model
                           # Use user-selected order
                           model_arima = ARIMA(df_arima['price'], order=arima_order_selected)
                           model_fit = model_arima.fit()
                           
                           # Forecast
                           forecast_steps = forecast_horizon
                           forecast_result = model_fit.get_forecast(steps=forecast_steps)
                           forecast_values = forecast_result.predicted_mean
                           conf_int = forecast_result.conf_int(alpha=0.05) # 95% confidence interval
                           
                           # Create forecast index (future dates)
                           forecast_index = pd.date_range(start=df_arima.index[-1] + pd.Timedelta(days=1), periods=forecast_steps, freq='D')
                           
                           # Plot ARIMA forecast
                           fig_arima = go.Figure()
                           # Actual data
                           fig_arima.add_trace(go.Scatter(x=df_arima.index, y=df_arima['price'], mode='lines', name='Actual Price'))
                           # Forecast
                           fig_arima.add_trace(go.Scatter(x=forecast_index, y=forecast_values, mode='lines', name='Forecast', line=dict(color='red')))
                           # Confidence Intervals
                           fig_arima.add_trace(go.Scatter(x=forecast_index, y=conf_int.iloc[:, 0], mode='lines', name='Lower CI', line=dict(width=0), showlegend=False))
                           fig_arima.add_trace(go.Scatter(x=forecast_index, y=conf_int.iloc[:, 1], mode='lines', name='Upper CI', fill='tonexty', line=dict(width=0), fillcolor='rgba(255, 0, 0, 0.2)', showlegend=True))
                           
                           fig_arima.update_layout(title=f"{selected_coin_name} Forecast (ARIMA{arima_order_selected})",
                                                 xaxis_title="Date", yaxis_title=f"Price ({currency_upper})")
                           st.plotly_chart(fig_arima, use_container_width=True)
                           
                           if st.checkbox("Show ARIMA Forecast Data", key="arima_data"):
                               forecast_df_display = pd.DataFrame({
                                   'Forecast': forecast_values,
                                   'Lower_CI': conf_int.iloc[:, 0],
                                   'Upper_CI': conf_int.iloc[:, 1]
                               }, index=forecast_index)
                               st.dataframe(forecast_df_display.style.format("{:,.4f}"))
                               
                      except Exception as e:
                          st.error(f"Error running ARIMA model with order {arima_order_selected}: {e}")
                          st.info("ARIMA models can be sensitive to the order (p,d,q) and data stationarity. Ensure the differencing order 'd' is appropriate based on the ADF test, or try different orders.")

             # --- Tab 3: Autocorrelation Analysis --- 
             with tab3:
                 st.subheader("Autocorrelation Function (ACF) and Partial Autocorrelation Function (PACF)")
                 st.markdown("Used to help identify potential orders for ARIMA models (p from PACF, q from ACF). Generally applied to stationary series (e.g., daily returns or differenced price).")
                 
                 # Calculate daily returns for ACF/PACF analysis
                 daily_returns = df_arima['price'].pct_change().dropna() * 100
                 
                 if not daily_returns.empty:
                     try:
                         # Plot ACF and PACF using matplotlib
                         fig_acf_pacf, axes = plt.subplots(1, 2, figsize=(12, 4))
                         plot_acf(daily_returns, lags=40, ax=axes[0], title='ACF of Daily Returns')
                         plot_pacf(daily_returns, lags=40, ax=axes[1], title='PACF of Daily Returns')
                         plt.tight_layout()
                         st.pyplot(fig_acf_pacf)
                         plt.close(fig_acf_pacf) # Close plot
                     except Exception as e:
                         st.error(f"Could not plot ACF/PACF: {e}")
                 else:
                     st.warning("Not enough data to calculate daily returns for ACF/PACF plots.")


    elif not hist_df_orig.empty and len(hist_df_orig) <= 30:
        st.warning(f"Historical data loaded ({len(hist_df_orig)} points), but more data (ideally 90+ days, preferably 1+ year) is recommended for robust forecasting. Try a longer historical period.")
    elif not hist_df_orig.empty and 'price' not in hist_df_orig.columns:
         st.warning("Historical data fetched, but 'price' column is missing.")
    else:
        st.warning("Could not fetch or process sufficient historical data for forecasting. Check API status or try again later.")

elif not coin_map:
     st.error("Application cannot function without the coin list. Please check API status.")
elif selected_coin_id is None and selected_coin_name:
    st.error(f"Could not find ID for selected coin: {selected_coin_name}")
else:
    st.info("⬅️ Please select a coin and options from the sidebar to start analysis.")

# Remove the previous placeholder section
# st.markdown("--- ")
# st.markdown("### Advanced Models (Future Implementation)")
# st.info("Support for ARIMA/SARIMA (for price) and GARCH (for volatility) models can be added here.") 