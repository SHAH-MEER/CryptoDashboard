import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # Import graph_objects

st.set_page_config(page_title="Global Crypto Market", page_icon="��", layout="wide")

st.title("🌍 Global Cryptocurrency Market Overview")

# --- Helper Function ---
@st.cache_data(ttl=300) # Cache for 5 minutes
def get_global_market_data():
    url = "https://api.coingecko.com/api/v3/global"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['data'] # The actual data is nested under the 'data' key
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching global market data: {e}")
        return None
    except KeyError:
        st.error("Unexpected format received from global market data API.")
        return None

# --- Main Page ---
global_data = get_global_market_data()

if global_data:
    st.subheader("Key Global Metrics")

    # Select active currency for display (use USD as default if not found)
    active_currency = st.selectbox("Select Currency for Global Metrics", 
                                   list(global_data['total_market_cap'].keys()),
                                   index=list(global_data['total_market_cap'].keys()).index('usd') if 'usd' in global_data['total_market_cap'] else 0
                                   )
    curr_upper = active_currency.upper()

    total_mcap = global_data['total_market_cap'].get(active_currency, 0)
    total_vol = global_data['total_volume'].get(active_currency, 0)
    mcap_change_24h = global_data['market_cap_change_percentage_24h_usd'] # Usually provided in USD
    btc_dominance = global_data.get('market_cap_percentage', {}).get('btc', 0)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Market Cap", f"{total_mcap:,.0f} {curr_upper}", f"{mcap_change_24h:.2f}% (24h)")
    col2.metric("Total 24h Volume", f"{total_vol:,.0f} {curr_upper}")
    col3.metric("Active Cryptocurrencies", global_data['active_cryptocurrencies'])

    st.divider() # Add a divider
    
    # --- Add Market Cap by Currency Chart ---
    st.subheader("Total Market Cap by Currency")
    mcap_by_currency = global_data['total_market_cap']
    mcap_df = pd.DataFrame(mcap_by_currency.items(), columns=['Currency', 'Market Cap'])
    mcap_df['Currency'] = mcap_df['Currency'].str.upper() # Uppercase currency codes
    
    fig_mcap_curr = px.bar(mcap_df, x='Currency', y='Market Cap', 
                           title='Global Crypto Market Cap in Different Currencies', 
                           labels={'Market Cap': 'Total Market Cap'})
    fig_mcap_curr.update_layout(yaxis_title=None) # Remove y-axis title for cleaner look with labels
    st.plotly_chart(fig_mcap_curr, use_container_width=True)
    
    st.divider() # Add another divider

    # Add BTC Dominance Gauge Chart
    st.subheader("Bitcoin (BTC) Dominance")
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = btc_dominance,
        title = {'text': "BTC Market Cap Dominance (%)"},
        gauge = {'axis': {'range': [0, 100]}, 
                 'bar': {'color': "orange"},
                 'steps' : [
                     {'range': [0, 40], 'color': "lightgray"},
                     {'range': [40, 60], 'color': "gray"}],
                 'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 50}} # Example threshold
    ))
    fig_gauge.update_layout(height=250, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.divider()

    st.subheader("Market Dominance")
    market_cap_percentage = global_data['market_cap_percentage']
    
    # Convert dictionary to DataFrame for easier plotting
    dominance_df = pd.DataFrame(market_cap_percentage.items(), columns=['Coin', 'Dominance (%)'])
    dominance_df = dominance_df.sort_values(by='Dominance (%)', ascending=False).head(10) # Show top 10

    # Display as a pie chart
    fig = px.pie(dominance_df, values='Dominance (%)', names='Coin', 
                 title='Top 10 Cryptocurrency Market Dominance by Market Cap', 
                 hole=0.3) # Donut chart style
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

    # Display as a table as well
    st.dataframe(dominance_df.style.format({'Dominance (%)': '{:.2f}%'}), hide_index=True)

    st.divider()

    # Display as Treemap
    st.subheader("Market Dominance Treemap")
    # Use the full dominance data for a more complete treemap
    full_dominance_df = pd.DataFrame(global_data['market_cap_percentage'].items(), columns=['Coin', 'Dominance (%)'])
    # Add a dummy parent column for the treemap structure if needed, or just use 'Coin'
    full_dominance_df['parent'] = 'Market' # Assign a common parent

    fig_treemap = px.treemap(full_dominance_df, 
                             path=['parent', 'Coin'], # Define the hierarchy
                             values='Dominance (%)',
                             title='Market Dominance Treemap',
                             color='Dominance (%)', # Color based on dominance value
                             color_continuous_scale='YlGnBu') # Choose a color scale
    fig_treemap.update_layout(margin = dict(t=50, l=25, r=25, b=25))
    st.plotly_chart(fig_treemap, use_container_width=True)

else:
    st.warning("Could not fetch global market data. Check API status or try again later.") 