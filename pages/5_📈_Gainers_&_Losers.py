import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import utils # Import the utility module

st.set_page_config(page_title="Gainers & Losers", page_icon="💹", layout="wide")

st.title("💹 Top 24h Gainers & Losers")
st.markdown("Based on the top 250 coins by market cap.")

# --- Helper Function (Similar to Dashboard's get_top_coins) ---
# Function moved to utils.py
# @st.cache_data(ttl=180) # Cache for 3 minutes
# def get_market_data(currency, num_coins=250):
#     ...

# --- Sidebar ---
st.sidebar.header("⚙️ Options")
currency = st.sidebar.selectbox(
    "Select Currency", 
    ["usd", "eur", "gbp", "jpy"], # Focus on fiat for price/volume
    key="gainers_losers_currency"
)
num_results = st.sidebar.slider(
    "Number of Top Gainers/Losers to Display", 
    min_value=5, max_value=50, value=10, step=5, 
    key="gainers_losers_num"
)

# --- Load Market Data ---
# Use the specific function from utils
market_df = utils.get_market_data_for_gainers_losers(currency, num_coins=250) 

if not market_df.empty:
    # Ensure change_24h is numeric for sorting
    market_df['change_24h'] = pd.to_numeric(market_df['change_24h'], errors='coerce')
    market_df = market_df.dropna(subset=['change_24h']) # Drop rows where conversion failed
    
    if not market_df.empty:
        # --- Sort Data ---
        gainers = market_df.sort_values(by="change_24h", ascending=False).head(num_results)
        losers = market_df.sort_values(by="change_24h").head(num_results)

        # --- Display Top Gainer/Loser Metrics ---
        col_metric1, col_metric2 = st.columns(2)
        if not gainers.empty:
            top_gainer = gainers.iloc[0]
            col_metric1.metric(
                label=f"🚀 Top Gainer: {top_gainer['name']}", 
                value=f"{top_gainer['change_24h']:.2f}%",
                help=f"Current Price: {top_gainer['price']:,.4f} {currency.upper()}"
            )
        else:
             col_metric1.info("No gainer data found.")
             
        if not losers.empty:
            top_loser = losers.iloc[0]
            col_metric2.metric(
                label=f"📉 Top Loser: {top_loser['name']}",
                value=f"{top_loser['change_24h']:.2f}%",
                help=f"Current Price: {top_loser['price']:,.4f} {currency.upper()}"
            )
        else:
             col_metric2.info("No loser data found.")

        st.divider()

        # --- Create Tabs for Gainers and Losers ---
        tab1, tab2 = st.tabs(["📈 Top Gainers", "📉 Top Losers"])

        # --- Tab 1: Gainers ---
        with tab1:
            if not gainers.empty:
                st.subheader(f"Top {num_results} Gainers (24h)")
                
                # Display Table
                st.dataframe(
                    gainers,
                    column_config={
                        "name": "Coin",
                        "symbol": "Symbol",
                        "price": st.column_config.NumberColumn(f"Price ({currency.upper()})", format="%.4f"),
                        "change_24h": st.column_config.NumberColumn("Change (24h)", format="%.2f%%"),
                        "total_volume": st.column_config.NumberColumn(f"Volume ({currency.upper()})", format="%.0f"),
                    },
                    hide_index=True
                )
                
                # Display Bar Chart
                fig_gainers = px.bar(gainers, x='name', y='change_24h',
                                     title=f"Top {num_results} Gainers by 24h Change",
                                     color='change_24h', color_continuous_scale='greens',
                                     hover_data=['symbol', 'price', 'total_volume'],
                                     labels={'name':'Coin', 'change_24h':'Change (%)'})
                fig_gainers.update_layout(xaxis_title="Coin", yaxis_title="24h Change (%)")
                st.plotly_chart(fig_gainers, use_container_width=True)
            else:
                st.info("No data available for gainers.")

        # --- Tab 2: Losers ---
        with tab2:
            if not losers.empty:
                st.subheader(f"Top {num_results} Losers (24h)")
                
                # Display Table
                st.dataframe(
                    losers,
                     column_config={
                        "name": "Coin",
                        "symbol": "Symbol",
                        "price": st.column_config.NumberColumn(f"Price ({currency.upper()})", format="%.4f"),
                        "change_24h": st.column_config.NumberColumn("Change (24h)", format="%.2f%%"),
                        "total_volume": st.column_config.NumberColumn(f"Volume ({currency.upper()})", format="%.0f"),
                    },
                    hide_index=True
                )
                
                # Display Bar Chart (Reverse color scale for losers)
                fig_losers = px.bar(losers.sort_values('change_24h'), x='name', y='change_24h',
                                    title=f"Top {num_results} Losers by 24h Change",
                                    color='change_24h', color_continuous_scale='reds_r', # Reversed Reds
                                    hover_data=['symbol', 'price', 'total_volume'],
                                    labels={'name':'Coin', 'change_24h':'Change (%)'})
                fig_losers.update_layout(xaxis_title="Coin", yaxis_title="24h Change (%)")
                st.plotly_chart(fig_losers, use_container_width=True)
            else:
                st.info("No data available for losers.")
                
        # --- Optional: Scatter plot Change vs Volume ---
        st.divider()
        st.subheader("24h Change vs. Volume (Top 250 Coins)")
        if not market_df.empty and 'total_volume' in market_df.columns:
            # Ensure volume is numeric and positive for log scale
            market_df['total_volume'] = pd.to_numeric(market_df['total_volume'], errors='coerce')
            plot_df_scatter = market_df[(market_df['total_volume'] > 0) & market_df['change_24h'].notna()].copy()
            if not plot_df_scatter.empty:
                fig_scatter = px.scatter(plot_df_scatter, 
                                         x="total_volume", 
                                         y="change_24h", 
                                         hover_name="name",
                                         hover_data=['symbol', 'price'],
                                         color="change_24h",
                                         color_continuous_scale=px.colors.diverging.RdYlGn, # Use diverging scale
                                         log_x=True, # Use log scale for volume
                                         title="24h Change vs. Log Volume",
                                         labels={'total_volume': f"Volume ({currency.upper()}) (Log Scale)",
                                                 'change_24h': "Change (%)"})
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                 st.info("Not enough valid data for the Change vs. Volume scatter plot.")
        else:
            st.info("Volume data missing, cannot generate scatter plot.")
            
    else:
         st.warning("Market data could not be processed after fetching (e.g., missing change data).")
else:
    st.error("Failed to load market data from the API for Gainers & Losers. Please check connection or try again later.") 