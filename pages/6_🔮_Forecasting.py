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

st.set_page_config(page_title="Forecasting & Analysis", page_icon="🔮", layout="wide")

st.title("🔮 Time Series Forecasting & Analysis")

st.warning("**Disclaimer:** Cryptocurrency price forecasting is highly speculative and notoriously difficult. These models are for educational purposes only and should **not** be considered financial advice. Past performance is not indicative of future results.")

# --- Helper Functions (Copied - consider refactoring) ---

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
        df_hist = pd.DataFrame(prices, columns=["timestamp", "price"])
        df_hist["date"] = pd.to_datetime(df_hist["timestamp"], unit="ms")
        df_hist = df_hist.drop_duplicates(subset=['date']).sort_values(by='date')
        df_hist = df_hist.set_index('date')
        df_hist = df_hist[['price']]
        
        # Ensure daily frequency and forward fill missing values
        df_hist = df_hist.asfreq('D')
        df_hist['price'] = df_hist['price'].ffill() # Forward fill gaps created by asfreq
        df_hist = df_hist.dropna() # Drop any remaining NaNs (e.g., at the start)

        return df_hist
    except requests.exceptions.HTTPError as http_err:
        status_code = response.status_code
        if status_code == 429:
             st.warning(f"Rate limit hit fetching historical data. Please wait.")
        elif status_code == 401:
             st.error(f"Error 401: Unauthorized. Check API key if applicable.")
        elif status_code == 404:
            st.warning(f"Historical data not found ({status_code}).")
        else:
             st.warning(f"Could not fetch historical data (HTTP Error {status_code}).")
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        st.warning(f"Error fetching historical data: {e}")
        return pd.DataFrame()
    except KeyError:
        st.warning("Historical price data format unexpected or missing.")
        return pd.DataFrame()

# --- ADF Test Function ---
def run_adf_test(series):
    result = adfuller(series.dropna())
    p_value = result[1]
    is_stationary = p_value < 0.05
    return is_stationary, p_value

# --- Sidebar --- 
st.sidebar.header("⚙️ Forecasting Options")
coin_map = get_coin_list()

selected_coin_id = None
selected_coin_name = None

if coin_map:
    all_coin_names = sorted([name.title() for name in coin_map.keys()])
    default_coin_display_name = "Bitcoin"
    try:
        default_index = all_coin_names.index(default_coin_display_name)
    except ValueError:
        default_index = 0

    selected_coin_name = st.sidebar.selectbox(
        "Select Coin (Type to search)", 
        options=all_coin_names, 
        index=default_index,
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
        options=[90, 180, 365], 
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

else:
    st.sidebar.error("Could not load coin list from API.")
    currency = "usd"
    currency_upper = "USD"

# --- Main Page ---
if selected_coin_id and selected_coin_name:
    
    # Fetch Data once
    hist_df_orig = get_historical_data(selected_coin_id, currency, days=days_history)
    
    if not hist_df_orig.empty and len(hist_df_orig) > 30: # Need more data for ARIMA/GARCH
        
        st.header(f"Forecasting & Analysis for {selected_coin_name} ({currency_upper})")
        
        # Create Tabs for different models
        tab1, tab2, tab3 = st.tabs(["🔮 Prophet", "📈 ARIMA", "📊 Autocorrelation (ACF/PACF)"])
        
        # --- Prophet Tab --- 
        with tab1:
            st.subheader("Prophet Model Forecast")
            try:
                # Prepare data for Prophet
                hist_df_prophet = hist_df_orig.reset_index().rename(columns={'date': 'ds', 'price': 'y'})
                
                # Initialize Prophet model 
                m = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True,
                            changepoint_prior_scale=0.05) 
                m.fit(hist_df_prophet)
                future = m.make_future_dataframe(periods=forecast_horizon)
                forecast_df = m.predict(future)

                # Display Results
                st.markdown(f"**Forecast for the next {forecast_horizon} days**")
                fig_forecast = plot_plotly(m, forecast_df)
                fig_forecast.update_layout(title=f"{selected_coin_name} Price Forecast vs Actuals", 
                                           xaxis_title="Date", yaxis_title=f"Price ({currency_upper})")
                st.plotly_chart(fig_forecast, use_container_width=True)
                
                st.markdown("**Forecast Components**")
                fig_components = plot_components_plotly(m, forecast_df)
                st.plotly_chart(fig_components, use_container_width=True)
                
                if st.checkbox("Show Prophet Forecast Data", key="prophet_show_data"): 
                    st.dataframe(forecast_df[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(forecast_horizon).style.format({
                         'yhat': '{:,.2f}'.format, 'yhat_lower': '{:,.2f}'.format, 'yhat_upper': '{:,.2f}'.format
                     }))
            except Exception as e:
                st.error(f"An error occurred during Prophet forecasting: {e}")

        # --- ARIMA Tab --- 
        with tab2:
            st.subheader("ARIMA Model Forecast")
            try:
                # Stationarity Check
                is_stationary, p_value = run_adf_test(hist_df_orig['price'])
                st.write(f"**Stationarity Check (ADF Test):**")
                st.write(f"P-value: {p_value:.4f}")
                if is_stationary:
                    st.success("The price series is likely stationary (p < 0.05). ARIMA will use d=0.")
                    d = 0
                else:
                    st.warning("The price series is likely non-stationary (p >= 0.05). Differencing (d=1) will be applied.")
                    d = 1
                
                # ARIMA Model (using p=5, d determined by test, q=0 as a common starting point)
                # Note: Proper order selection (p,q) requires ACF/PACF analysis, which is omitted here for simplicity.
                arima_order = (5, d, 0) 
                st.write(f"Fitting ARIMA{arima_order} model... (This might take a moment)")
                
                model = ARIMA(hist_df_orig['price'], order=arima_order)
                model_fit = model.fit()
                st.write("Model fitting complete.")

                # Forecast
                forecast_steps = forecast_horizon
                forecast_result = model_fit.get_forecast(steps=forecast_steps)
                forecast_values = forecast_result.predicted_mean
                conf_int = forecast_result.conf_int(alpha=0.05) # 95% confidence interval
                
                # Create forecast dates
                last_date = hist_df_orig.index[-1]
                forecast_index = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_steps, freq='D')
                
                # Combine forecast into a dataframe
                forecast_df_arima = pd.DataFrame({
                    'Forecast': forecast_values,
                    'Lower CI': conf_int.iloc[:, 0],
                    'Upper CI': conf_int.iloc[:, 1]
                }, index=forecast_index)

                # Plot ARIMA forecast
                st.markdown(f"**ARIMA{arima_order} Forecast for the next {forecast_horizon} days**")
                fig_arima = go.Figure()
                # Plot historical data
                fig_arima.add_trace(go.Scatter(x=hist_df_orig.index, y=hist_df_orig['price'], mode='lines', name='Historical Price'))
                # Plot forecast
                fig_arima.add_trace(go.Scatter(x=forecast_df_arima.index, y=forecast_df_arima['Forecast'], mode='lines', name='Forecast', line=dict(color='red')))
                # Plot confidence intervals
                fig_arima.add_trace(go.Scatter(x=forecast_df_arima.index, y=forecast_df_arima['Upper CI'], mode='lines', name='Upper 95% CI', line=dict(dash='dash', color='rgba(255,0,0,0.3)')))
                fig_arima.add_trace(go.Scatter(x=forecast_df_arima.index, y=forecast_df_arima['Lower CI'], mode='lines', name='Lower 95% CI', line=dict(dash='dash', color='rgba(255,0,0,0.3)'), fill='tonexty', fillcolor='rgba(255,0,0,0.1)'))
                
                fig_arima.update_layout(title=f"{selected_coin_name} ARIMA{arima_order} Forecast", 
                                        xaxis_title="Date", yaxis_title=f"Price ({currency_upper})")
                st.plotly_chart(fig_arima, use_container_width=True)
                
                if st.checkbox("Show ARIMA Forecast Data", key="arima_show_data"): 
                    st.dataframe(forecast_df_arima.style.format('{:,.2f}'))

            except Exception as e:
                st.error(f"An error occurred during ARIMA forecasting: {e}")
                st.error("This might happen with insufficient data, model convergence issues, or memory constraints.")

        # --- Autocorrelation (ACF/PACF) Tab --- 
        with tab3:
            st.subheader("Autocorrelation Analysis on Daily Returns")
            st.info("ACF shows the correlation of the series with its lags. PACF shows the correlation after removing effects of intermediate lags. These help identify potential patterns (e.g., AR/MA components for ARIMA).")
            try:
                # Calculate log returns 
                returns = np.log(hist_df_orig['price'] / hist_df_orig['price'].shift(1)).dropna() * 100
                
                if returns.empty or len(returns) < 20: # Need some data for ACF/PACF
                    st.warning(f"Not enough return data ({len(returns)} points) for autocorrelation analysis.")
                else:
                    # Determine lags (e.g., up to 40 or based on data length)
                    max_lags = min(40, len(returns) // 2 - 1)
                    if max_lags < 1:
                         st.warning("Not enough data points to calculate meaningful lags.")
                    else:
                        # Plot ACF
                        st.markdown("**Autocorrelation Function (ACF)**")
                        fig_acf, ax_acf = plt.subplots(figsize=(10, 4))
                        plot_acf(returns, lags=max_lags, ax=ax_acf, zero=False) # zero=False excludes lag 0
                        ax_acf.set_title('ACF of Daily Log Returns')
                        ax_acf.set_xlabel('Lag')
                        ax_acf.set_ylabel('Autocorrelation')
                        st.pyplot(fig_acf)
                        plt.close(fig_acf) # Close the figure to free memory

                        # Plot PACF
                        st.markdown("**Partial Autocorrelation Function (PACF)**")
                        fig_pacf, ax_pacf = plt.subplots(figsize=(10, 4))
                        plot_pacf(returns, lags=max_lags, ax=ax_pacf, zero=False, method='ols') # method='ols' is common
                        ax_pacf.set_title('PACF of Daily Log Returns')
                        ax_pacf.set_xlabel('Lag')
                        ax_pacf.set_ylabel('Partial Autocorrelation')
                        st.pyplot(fig_pacf)
                        plt.close(fig_pacf) # Close the figure

            except Exception as e:
                st.error(f"An error occurred during autocorrelation analysis: {e}")
        
    elif not hist_df_orig.empty:
        st.warning(f"Historical data loaded ({len(hist_df_orig)} points), but may be insufficient for robust analysis (need > 30 points). Try a longer historical period.")
    else:
        st.warning("Could not fetch or process historical data for the selected coin and timeframe.")

elif not coin_map:
     st.error("Application cannot function without the coin list. Please check API status.")
else:
    st.info("⬅️ Please select a coin from the sidebar to start analysis.")

# Remove the previous placeholder section
# st.markdown("--- ")
# st.markdown("### Advanced Models (Future Implementation)")
# st.info("Support for ARIMA/SARIMA (for price) and GARCH (for volatility) models can be added here.") 