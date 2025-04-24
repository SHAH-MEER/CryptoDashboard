import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import utils # Import the new utility module

st.set_page_config(page_title="Crypto Dashboard", page_icon="📈", layout="wide")

# Title
st.title("📈 Crypto Dashboard")

# --- Helper Functions ---
# API functions are now in utils.py
# @st.cache_data(ttl=600) -> Moved to utils.get_top_coins
# def get_top_coins(currency, per_page):
#     ...

# @st.cache_data(ttl=7200) -> Moved to utils.get_historical_data
# def get_historical_data(coin_id, currency, days):
#     ...

# --- Sidebar --- 
st.sidebar.header("⚙️ Options")
currency = st.sidebar.selectbox("Select Currency", ["usd", "eur", "gbp", "jpy"], key="dashboard_currency")
# Consider reducing the default/max if rate limits persist
per_page = st.sidebar.slider("Number of Coins", 1, 100, 25, key="dashboard_per_page") 
days_history = st.sidebar.selectbox("Select Historical Data Timeframe (Days)", [7, 30, 90, 365], index=1, key="dashboard_days")

# --- Main Page ---

st.subheader(f"Top {per_page} Cryptocurrencies by Market Cap")
# Call function from utils module
df_coins = utils.get_top_coins(currency, per_page)

if not df_coins.empty:
    # Display top coins table (remains outside tabs)
    # Check if 'sparkline_7d_prices' column exists before configuring it
    column_config = {
        "name": "Coin",
        "symbol": "Symbol",
        "current_price": st.column_config.NumberColumn(f"Price ({currency.upper()})", format="%.4f"),
        "price_change_percentage_24h": st.column_config.NumberColumn("24h Change", format="%.2f%%"),
        "market_cap": st.column_config.NumberColumn(f"Market Cap ({currency.upper()})", format="%.0f"),
        "total_volume": st.column_config.NumberColumn(f"Volume ({currency.upper()})", format="%.0f"),
        "market_cap_rank": "Rank",
        # Conditionally add sparkline config only if the column exists
        "sparkline_7d_prices": st.column_config.LineChartColumn("7d Trend", width="medium") if 'sparkline_7d_prices' in df_coins.columns else None,
        # Hide other raw columns
        "sparkline_in_7d": None, "id": None, "image": None, "fully_diluted_valuation": None, "high_24h": None, "low_24h": None,
        "price_change_24h": None, "market_cap_change_24h": None, "market_cap_change_percentage_24h": None,
        "circulating_supply": None, "total_supply": None, "max_supply": None, "ath": None, "ath_change_percentage": None,
        "ath_date": None, "atl": None, "atl_change_percentage": None, "atl_date": None, "roi": None, "last_updated": None
    }
    # Remove None values from config
    column_config = {k: v for k, v in column_config.items() if v is not None}
    
    st.dataframe(
        df_coins,
        column_config=column_config,
        hide_index=True
    )
    
    st.divider()
    
    # --- Create Tabs for Visuals and Details --- 
    tab1, tab2 = st.tabs(["📊 Market Visuals", "🔎 Selected Coin Detail"])
    
    # --- Tab 1: Market Visuals ---
    with tab1:
        # Add 24h Price Change Bar Chart
        st.subheader("24h Price Change Percentage")
        # Ensure the change column is numeric for sorting/plotting
        df_coins['price_change_percentage_24h'] = pd.to_numeric(df_coins['price_change_percentage_24h'], errors='coerce')
        df_coins_sorted_change = df_coins.dropna(subset=['price_change_percentage_24h']).sort_values(by='price_change_percentage_24h', ascending=False)
        if not df_coins_sorted_change.empty:
            fig_change = px.bar(df_coins_sorted_change, x='name', y='price_change_percentage_24h', 
                                title=f'24h Price Change (%) for Top {len(df_coins_sorted_change)} Coins',
                                color='price_change_percentage_24h', color_continuous_scale=px.colors.diverging.RdYlGn,
                                labels={'name':'Coin', 'price_change_percentage_24h':'Change (%)'})
            fig_change.update_layout(xaxis_title='Coin', yaxis_title='Change (%)')
            st.plotly_chart(fig_change, use_container_width=True)
        else:
             st.info("No valid 24h change data available for the bar chart.")

        st.divider()
        
        # Add Market Cap vs Volume Scatter Plot
        st.subheader("Market Cap vs. 24h Volume")
        # Ensure required columns are numeric
        df_coins['market_cap'] = pd.to_numeric(df_coins['market_cap'], errors='coerce')
        df_coins['total_volume'] = pd.to_numeric(df_coins['total_volume'], errors='coerce')
        plot_df = df_coins[(df_coins['market_cap'] > 0) & (df_coins['total_volume'] > 0)].copy()
        plot_df['price_change_cat'] = plot_df['price_change_percentage_24h'].apply(lambda x: 'Positive' if pd.notna(x) and x >= 0 else ('Negative' if pd.notna(x) else 'Neutral'))
        if not plot_df.empty:
            fig_scatter = px.scatter(plot_df, x='market_cap', y='total_volume', hover_name='name', 
                                    hover_data=['symbol', 'current_price', 'price_change_percentage_24h'],
                                    title=f"Market Cap vs. 24h Volume (Top {len(plot_df)} Coins)",
                                    color='price_change_cat', color_discrete_map={'Positive': 'green', 'Negative': 'red', 'Neutral': 'grey'},
                                    log_x=True, log_y=True,
                                    labels={'market_cap': f'Market Cap ({currency.upper()}) (Log Scale)',
                                            'total_volume': f'24h Volume ({currency.upper()}) (Log Scale)',
                                            'price_change_cat': '24h Change'})
            fig_scatter.update_layout(legend_title_text='24h Price Change')
            st.plotly_chart(fig_scatter, use_container_width=True)
        else: st.info("Not enough data with positive Market Cap and Volume for scatter plot.")

        st.divider()
        
        # Add Distribution Pie Charts side-by-side
        col_pie1, col_pie2 = st.columns(2)
        with col_pie1:
             st.subheader("Market Cap Distribution")
             pie_df = df_coins[pd.to_numeric(df_coins['market_cap'], errors='coerce') > 0].copy()
             if not pie_df.empty:
                 fig_pie_mcap = px.pie(pie_df, values='market_cap', names='name', 
                                    title=f'Market Cap Distribution (Top {len(pie_df)})',
                                    hover_data=['symbol'], labels={'market_cap': 'Market Cap', 'name': 'Coin'})
                 fig_pie_mcap.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
                 fig_pie_mcap.update_layout(margin=dict(l=20, r=20, t=30, b=20)) # Adjust margins for labels
                 st.plotly_chart(fig_pie_mcap, use_container_width=True)
             else: st.info("No positive Market Cap data for pie chart.")
        
        with col_pie2:
             st.subheader("24h Volume Distribution")
             vol_pie_df = df_coins[pd.to_numeric(df_coins['total_volume'], errors='coerce') > 0].copy()
             if not vol_pie_df.empty:
                 fig_pie_vol = px.pie(vol_pie_df, values='total_volume', names='name', 
                                   title=f'24h Volume Distribution (Top {len(vol_pie_df)})',
                                   hover_data=['symbol'], labels={'total_volume': 'Volume', 'name': 'Coin'})
                 fig_pie_vol.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
                 fig_pie_vol.update_layout(margin=dict(l=20, r=20, t=30, b=20)) # Adjust margins
                 st.plotly_chart(fig_pie_vol, use_container_width=True)
             else: st.info("No positive Volume data for pie chart.")

    # --- Tab 2: Selected Coin Detail ---
    with tab2:
        # Coin Selection for details - ensure 'name' column exists
        if 'name' in df_coins.columns and not df_coins['name'].empty:
            coin_options = df_coins["name"].tolist()
            selected_coin_name = st.selectbox(
                "Select a Coin for Detailed View", 
                options=coin_options,
                index=0 if coin_options else None,
                key="dashboard_select_coin"
            )
        else:
            selected_coin_name = None
            st.info("No coins available for selection.")
    
        if selected_coin_name:
            # Ensure 'id' column exists
            if 'id' in df_coins.columns:
                selected_coin_data = df_coins[df_coins["name"] == selected_coin_name].iloc[0]
                coin_id = selected_coin_data.get("id", None)
            else:
                coin_id = None
                st.error("'id' column missing, cannot fetch historical data.")

            if coin_id:
                # Create inner tabs for Metrics and Chart
                inner_tab1, inner_tab2 = st.tabs(["📊 Key Metrics", "📈 Historical Chart"])
                
                with inner_tab1:
                    st.markdown(f"**Key Metrics for {selected_coin_name}**")
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    # Safely access data using .get() with defaults
                    price = selected_coin_data.get('current_price', 0)
                    change_24h = selected_coin_data.get('price_change_percentage_24h', 0)
                    mcap = selected_coin_data.get('market_cap', 0)
                    vol_24h = selected_coin_data.get('total_volume', 0)
                    col_m1.metric("Current Price", f"{price:,.4f} {currency.upper()}")
                    col_m2.metric("24h Change", f"{change_24h:.2f}%", delta=f"{change_24h:.2f}%")
                    col_m3.metric("Market Cap", f"{mcap:,.0f} {currency.upper()}")
                    col_m4.metric("24h Volume", f"{vol_24h:,.0f} {currency.upper()}")
                    st.markdown("&nbsp;") 
        
                with inner_tab2:
                    st.markdown(f"**{selected_coin_name} Price (Last {days_history} Days)**")
                    # Call function from utils module
                    historical_df = utils.get_historical_data(coin_id, currency, days=days_history)
        
                    if not historical_df.empty and 'date' in historical_df.columns and 'price' in historical_df.columns:
                        fig = px.line(historical_df, x="date", y="price", title=f"{selected_coin_name} Price")
                        fig.update_layout(xaxis_title='Date', yaxis_title=f'Price ({currency.upper()})')
                        st.plotly_chart(fig, use_container_width=True)
                    else: 
                        st.warning(f"Could not display historical data for {selected_coin_name}. Check API or data availability.")
            elif selected_coin_name: # Only show error if a coin was selected but ID failed
                 st.error(f"Could not retrieve ID for {selected_coin_name} to fetch details.")
                 
        elif not df_coins.empty: # Only show info if coins were loaded but none selected
            st.info("Select a coin from the list above to see details.")

else:
    st.warning("Could not fetch top cryptocurrency data. The API might be temporarily unavailable or rate limited. Please try again later.") 