import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Crypto Dashboard", page_icon="📈", layout="wide")

# Title
st.title("📈 Crypto Dashboard")

# --- Helper Functions ---
@st.cache_data(ttl=60)
def get_top_coins(currency, per_page):
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page={per_page}&sparkline=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        required_cols = ['name', 'symbol', 'current_price', 'price_change_percentage_24h', 
                         'market_cap', 'total_volume', 'market_cap_rank', 'sparkline_in_7d']
        for col in required_cols:
             if col not in df.columns:
                 if col == 'sparkline_in_7d':
                      df[col] = [None] * len(df)
                 else: 
                      df[col] = pd.NA
        df['sparkline_7d_prices'] = df['sparkline_in_7d'].apply(lambda x: x['price'] if isinstance(x, dict) and 'price' in x else None)
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching top coins: {e}")
        return pd.DataFrame()

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
        return df_hist
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 429:
            st.error(f"Rate limit hit fetching historical data. Please wait and try again.")
        else:
            st.error(f"HTTP error fetching historical data: {http_err} - Status Code: {response.status_code}")
        return pd.DataFrame(columns=["date", "price"])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching historical data: {e}")
        return pd.DataFrame(columns=["date", "price"])

# --- Sidebar --- 
st.sidebar.header("⚙️ Options")
currency = st.sidebar.selectbox("Select Currency", ["usd", "eur", "gbp", "jpy"], key="dashboard_currency")
per_page = st.sidebar.slider("Number of Coins", 1, 100, 25, key="dashboard_per_page") # Increased max coins
days_history = st.sidebar.selectbox("Select Historical Data Timeframe (Days)", [7, 30, 90, 365], index=1, key="dashboard_days")

# --- Main Page ---

st.subheader(f"Top {per_page} Cryptocurrencies by Market Cap")
df_coins = get_top_coins(currency, per_page)

if not df_coins.empty:
    # Display top coins table (remains outside tabs)
    st.dataframe(
        df_coins,
        column_config={
            "name": "Coin",
            "symbol": "Symbol",
            "current_price": st.column_config.NumberColumn(f"Price ({currency.upper()})", format="%.4f"),
            "price_change_percentage_24h": st.column_config.NumberColumn("24h Change", format="%.2f%%"),
            "market_cap": st.column_config.NumberColumn(f"Market Cap ({currency.upper()})", format="%.0f"),
            "total_volume": st.column_config.NumberColumn(f"Volume ({currency.upper()})", format="%.0f"),
            "market_cap_rank": "Rank",
            "sparkline_7d_prices": st.column_config.LineChartColumn("7d Trend", width="medium"), 
            "sparkline_in_7d": None, "id": None, "image": None, "fully_diluted_valuation": None, "high_24h": None, "low_24h": None,
            "price_change_24h": None, "market_cap_change_24h": None, "market_cap_change_percentage_24h": None,
            "circulating_supply": None, "total_supply": None, "max_supply": None, "ath": None, "ath_change_percentage": None,
            "ath_date": None, "atl": None, "atl_change_percentage": None, "atl_date": None, "roi": None, "last_updated": None
        },
        hide_index=True
    )
    
    st.divider()
    
    # --- Create Tabs for Visuals and Details --- 
    tab1, tab2 = st.tabs(["📊 Market Visuals", "🔎 Selected Coin Detail"])
    
    # --- Tab 1: Market Visuals ---
    with tab1:
        # Add 24h Price Change Bar Chart
        st.subheader("24h Price Change Percentage")
        df_coins_sorted_change = df_coins.sort_values(by='price_change_percentage_24h', ascending=False)
        fig_change = px.bar(df_coins_sorted_change, x='name', y='price_change_percentage_24h', 
                             title=f'24h Price Change (%) for Top {per_page} Coins',
                             color='price_change_percentage_24h', color_continuous_scale=px.colors.diverging.RdYlGn,
                             labels={'name':'Coin', 'price_change_percentage_24h':'Change (%)'})
        fig_change.update_layout(xaxis_title='Coin', yaxis_title='Change (%)')
        st.plotly_chart(fig_change, use_container_width=True)

        st.divider()
        
        # Add Market Cap vs Volume Scatter Plot
        st.subheader("Market Cap vs. 24h Volume")
        plot_df = df_coins[(df_coins['market_cap'] > 0) & (df_coins['total_volume'] > 0)].copy()
        plot_df['price_change_cat'] = plot_df['price_change_percentage_24h'].apply(lambda x: 'Positive' if x >= 0 else 'Negative')
        if not plot_df.empty:
            fig_scatter = px.scatter(plot_df, x='market_cap', y='total_volume', hover_name='name', 
                                    hover_data=['symbol', 'current_price', 'price_change_percentage_24h'],
                                    title=f"Market Cap vs. 24h Volume (Top {per_page} Coins)",
                                    color='price_change_cat', color_discrete_map={'Positive': 'green', 'Negative': 'red'},
                                    log_x=True, log_y=True,
                                    labels={'market_cap': f'Market Cap ({currency.upper()}) (Log Scale)',
                                            'total_volume': f'24h Volume ({currency.upper()}) (Log Scale)',
                                            'price_change_cat': '24h Change'})
            fig_scatter.update_layout(legend_title_text='24h Price Change')
            st.plotly_chart(fig_scatter, use_container_width=True)
        else: st.info("Not enough data for scatter plot.")

        st.divider()
        
        # Add Distribution Pie Charts side-by-side
        col_pie1, col_pie2 = st.columns(2)
        with col_pie1:
             st.subheader("Market Cap Distribution")
             pie_df = df_coins[pd.to_numeric(df_coins['market_cap'], errors='coerce') > 0].copy()
             if not pie_df.empty:
                 fig_pie_mcap = px.pie(pie_df, values='market_cap', names='name', 
                                    title=f'Market Cap Distribution (Top {per_page})',
                                    hover_data=['symbol'], labels={'market_cap': 'Market Cap', 'name': 'Coin'})
                 fig_pie_mcap.update_traces(textposition='inside', textinfo='percent', showlegend=False)
                 st.plotly_chart(fig_pie_mcap, use_container_width=True)
             else: st.info("No positive Market Cap data.")
        
        with col_pie2:
             st.subheader("24h Volume Distribution")
             vol_pie_df = df_coins[pd.to_numeric(df_coins['total_volume'], errors='coerce') > 0].copy()
             if not vol_pie_df.empty:
                 fig_pie_vol = px.pie(vol_pie_df, values='total_volume', names='name', 
                                   title=f'24h Volume Distribution (Top {per_page})',
                                   hover_data=['symbol'], labels={'total_volume': 'Volume', 'name': 'Coin'})
                 fig_pie_vol.update_traces(textposition='inside', textinfo='percent', showlegend=False)
                 st.plotly_chart(fig_pie_vol, use_container_width=True)
             else: st.info("No positive Volume data.")

    # --- Tab 2: Selected Coin Detail ---
    with tab2:
        # Coin Selection for details
        selected_coin_name = st.selectbox(
            "Select a Coin for Detailed View", 
            df_coins["name"],
            key="dashboard_select_coin"
        )
    
        if selected_coin_name:
            selected_coin_data = df_coins[df_coins["name"] == selected_coin_name].iloc[0]
            coin_id = selected_coin_data["id"]
    
            # Create inner tabs for Metrics and Chart
            inner_tab1, inner_tab2 = st.tabs(["📊 Key Metrics", "📈 Historical Chart"])
            
            with inner_tab1:
                st.markdown(f"**Key Metrics for {selected_coin_name}**")
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Current Price", f"{selected_coin_data['current_price']:,.2f} {currency.upper()}")
                col_m2.metric("24h Change", f"{selected_coin_data['price_change_percentage_24h']:.2f}%", delta=f"{selected_coin_data['price_change_percentage_24h']:.2f}%")
                col_m3.metric("Market Cap", f"{selected_coin_data['market_cap']:,.0f} {currency.upper()}")
                col_m4.metric("24h Volume", f"{selected_coin_data['total_volume']:,.0f} {currency.upper()}")
                st.markdown("&nbsp;") 
    
            with inner_tab2:
                st.markdown(f"**{selected_coin_name} Price (Last {days_history} Days)**")
                historical_df = get_historical_data(coin_id, currency, days=days_history)
    
                if not historical_df.empty:
                    fig = px.line(historical_df, x="date", y="price")
                    fig.update_layout(xaxis_title='Date', yaxis_title=f'Price ({currency.upper()})')
                    st.plotly_chart(fig, use_container_width=True)
                else: st.warning(f"Could not display historical data for {selected_coin_name}.")
        else:
            st.info("Select a coin from the list above to see details.")

else:
    st.warning("Could not fetch cryptocurrency data. Check API status or try again later.") 