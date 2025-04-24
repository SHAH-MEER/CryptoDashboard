import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import utils # Import the utility module

st.set_page_config(page_title="Global Crypto Market", page_icon="🌍", layout="wide")

st.title("🌍 Global Cryptocurrency Market Overview")

# --- Helper Function ---
# @st.cache_data(ttl=300) -> Moved to utils.get_global_market_data
# def get_global_market_data():
#     ...

# --- Load Data ---
data = utils.get_global_market_data()

if data:
    # --- Display Key Metrics ---
    st.subheader("Global Metrics")
    # Safely access nested data using .get() with default values
    total_market_cap_usd = data.get('total_market_cap', {}).get('usd', 0)
    total_volume_usd = data.get('total_volume', {}).get('usd', 0)
    active_cryptocurrencies = data.get('active_cryptocurrencies', 'N/A')
    market_cap_change_24h = data.get('market_cap_change_percentage_24h_usd', 0)
    btc_dominance = data.get('market_cap_percentage', {}).get('btc', 0)
    eth_dominance = data.get('market_cap_percentage', {}).get('eth', 0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Market Cap (USD)", f"${total_market_cap_usd:,.0f}", f"{market_cap_change_24h:.2f}% (24h)")
    col2.metric("Total 24h Volume (USD)", f"${total_volume_usd:,.0f}")
    col3.metric("Active Cryptocurrencies", f"{active_cryptocurrencies}")
    col4.metric("BTC Dominance", f"{btc_dominance:.2f}%")
    # col4.metric("ETH Dominance", f"{eth_dominance:.2f}%") # Optionally add ETH

    st.divider()

    # --- Visualizations ---
    col_viz1, col_viz2 = st.columns([0.3, 0.7]) # Adjust column widths

    with col_viz1:
        st.subheader("BTC Dominance Gauge")
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = btc_dominance,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Bitcoin Dominance (%)"},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "orange"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps' : [
                    {'range': [0, 40], 'color': 'lightblue'},
                    {'range': [40, 60], 'color': 'royalblue'}],
                'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 50}
            }
        ))
        fig_gauge.update_layout(height=300, margin=dict(l=10, r=10, t=50, b=10)) # Adjust layout
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_viz2:
        st.subheader("Market Cap Dominance (Top 10)")
        market_cap_percentage = data.get('market_cap_percentage', {})
        if market_cap_percentage:
            # Convert to DataFrame for easier plotting
            dom_df = pd.DataFrame(list(market_cap_percentage.items()), columns=['symbol', 'percentage'])
            dom_df['percentage'] = pd.to_numeric(dom_df['percentage'], errors='coerce')
            dom_df = dom_df.dropna().sort_values(by='percentage', ascending=False)
            
            # Add 'Other' category if more than 10 coins
            top_n = 10
            if len(dom_df) > top_n:
                other_percentage = dom_df.iloc[top_n:]['percentage'].sum()
                dom_df = dom_df.head(top_n)
                # Use pd.concat instead of append
                other_row = pd.DataFrame([{'symbol': 'Other', 'percentage': other_percentage}])
                dom_df = pd.concat([dom_df, other_row], ignore_index=True)

            # Treemap for Dominance
            fig_treemap = px.treemap(dom_df, path=[px.Constant("All Coins"), 'symbol'], values='percentage',
                                    title='Market Dominance Treemap',
                                    hover_data={'percentage': ':.2f%'})
            fig_treemap.update_layout(margin = dict(t=50, l=25, r=25, b=25))
            st.plotly_chart(fig_treemap, use_container_width=True)
            
        else:
            st.info("Market dominance data not available.")
    
    # Optional: Display raw data in expander
    with st.expander("Show Raw Global Data"):
        st.json(data)

else:
    st.error("Failed to load global market data from the API. Please check the connection or try again later.") 