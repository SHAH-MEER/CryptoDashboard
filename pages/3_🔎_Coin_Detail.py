import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from plotly.subplots import make_subplots
import utils # Import the utility module

st.set_page_config(page_title="Coin Detail", page_icon="🔎", layout="wide")

st.title("🔎 Coin Detail Page")

# --- Helper Functions ---
# Functions moved to utils.py:
# get_coin_list()
# get_coin_details(coin_id)
# get_historical_data(coin_id, currency, days)
# get_ohlc_data(coin_id, currency, days)

# --- Sidebar ---
st.sidebar.header("⚙️ Coin Selection")
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
        default_index = 0 # Default to the first coin if Bitcoin isn't found
        if all_coin_names: # Only warn if list is not empty
            st.sidebar.warning(f"Could not find '{default_coin_display_name}' in the coin list, defaulting to '{all_coin_names[0]}'.")
        else:
            st.sidebar.error("Coin list is empty.")
            
    # Use a single selectbox with all coin names
    selected_coin_name = st.sidebar.selectbox(
        "Select Coin (Type to search)", 
        options=all_coin_names, 
        index=default_index if all_coin_names else None, # Prevent index error if list is empty
        key="detail_coin_select_all"
    )
    
    if selected_coin_name:
        # Get the ID from the original map using the lowercase version of the selected name
        selected_coin_id = coin_map.get(selected_coin_name.lower())
    else:
        selected_coin_id = None 
        
    # Currency selection for market data
    currency = st.sidebar.selectbox(
        "Select Currency", 
        ["usd", "eur", "gbp", "jpy", "btc", "eth"], # Added crypto pairs
        key="detail_currency"
    )
    currency_upper = currency.upper()

    # Chart Type Selection
    chart_type = st.sidebar.radio(
        "Select Chart Type",
        ("Line Chart", "Candlestick Chart"),
        key="detail_chart_type"
    )
    
    # Timeframe Selection
    days_history = st.sidebar.selectbox(
        "Select Timeframe (Days)", 
        options=[7, 30, 90, 180, 365], # Added 7 days
        index=1, # Default to 30 days
        key="detail_days_history"
    )

else:
    st.sidebar.error("Could not load coin list from API.")
    currency = "usd"
    currency_upper = "USD"
    chart_type = "Line Chart"
    days_history = 30

# --- Main Page ---

if selected_coin_id and selected_coin_name:
    # Call function from utils module
    details = utils.get_coin_details(selected_coin_id)

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
            
            # Use selected currency and safely get data
            def get_market_metric(metric_key, default=0):
                return market_data.get(metric_key, {}).get(currency, default)
            
            def format_currency(value, default_val=0):
                 val = get_market_metric(value, default_val)
                 if val is None or val == default_val: return 'N/A'
                 # Basic check for large numbers to maybe format differently later?
                 if abs(val) > 1e6: return f"{currency_upper} {val:,.0f}"
                 return f"{currency_upper} {val:,.4f}" # Default to 4 decimal places for smaller prices
                 
            def format_percentage(value, default_val=0):
                val = get_market_metric(value, default_val)
                return f"{val:.2f}%" if val is not None else 'N/A'

            def format_date(metric_key, default_val=''):
                date_str = get_market_metric(metric_key, default_val)
                if not date_str: return 'N/A'
                try:
                    return pd.to_datetime(date_str).strftime('%Y-%m-%d %H:%M')
                except:
                    return 'N/A'

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Current Price", format_currency('current_price'), format_percentage('price_change_percentage_24h_in_currency') + " (24h)")
            col_m2.metric("Market Cap", format_currency('market_cap'), f"Rank #{details.get('market_cap_rank', 'N/A')}")
            col_m3.metric("24h Volume", format_currency('total_volume'))

            col_hilo1, col_hilo2 = st.columns(2)
            col_hilo1.metric("24h High", format_currency('high_24h'))
            col_hilo2.metric("24h Low", format_currency('low_24h'))

            st.divider()
            st.subheader("Performance")
            perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
            perf_col1.metric("7d Change", format_percentage('price_change_percentage_7d_in_currency'))
            perf_col2.metric("30d Change", format_percentage('price_change_percentage_30d_in_currency'))
            perf_col3.metric("1y Change", format_percentage('price_change_percentage_1y_in_currency'))
            # Sparkline (7d) - extract from details if available
            sparkline_data = market_data.get('sparkline_7d', {}).get('price')
            if sparkline_data:
                 spark_df = pd.DataFrame({'price': sparkline_data})
                 spark_df['index'] = range(len(spark_df)) # Add index for plotting
                 fig_spark = px.line(spark_df, x='index', y='price', height=60)
                 fig_spark.update_layout(showlegend=False, margin=dict(l=0,r=0,t=0,b=0), yaxis_visible=False, xaxis_visible=False)
                 perf_col4.markdown("**7d Trend**")
                 perf_col4.plotly_chart(fig_spark, use_container_width=True)

            st.divider()
            st.subheader("All-Time High / Low")
            col_ath1, col_ath2 = st.columns(2)
            col_ath1.metric("All-Time High", f"{format_currency('ath')}", f"{format_percentage('ath_change_percentage')} from ATH")
            col_ath1.caption(f"Date: {format_date('ath_date')}")
            col_ath2.metric("All-Time Low", f"{format_currency('atl')}", f"{format_percentage('atl_change_percentage')} from ATL")
            col_ath2.caption(f"Date: {format_date('atl_date')}")
            
            st.divider()
            st.subheader("Supply Information")
            circ_supply = market_data.get('circulating_supply')
            total_supply = market_data.get('total_supply')
            max_supply = market_data.get('max_supply')
            
            supply_data = {}
            if circ_supply is not None: supply_data['Circulating'] = circ_supply
            if total_supply is not None: supply_data['Total'] = total_supply
            if max_supply is not None: supply_data['Max'] = max_supply
            
            supply_col1, supply_col2 = st.columns([0.6, 0.4])
            with supply_col1:
                if circ_supply is not None: st.metric("Circulating Supply", f"{circ_supply:,.0f}")
                if total_supply is not None: st.metric("Total Supply", f"{total_supply:,.0f}")
                if max_supply is not None: st.metric("Max Supply", f"{max_supply:,.0f}")
                if not supply_data: st.info("Supply data not available.")

            with supply_col2:
                 if supply_data:
                     # Calculate relative supply if total or max is available
                     if total_supply is not None and circ_supply is not None and total_supply > 0:
                         circ_pct_of_total = (circ_supply / total_supply) * 100
                         st.progress(int(circ_pct_of_total), text=f"{circ_pct_of_total:.1f}% of Total Supply Circulating")
                     elif max_supply is not None and circ_supply is not None and max_supply > 0:
                         circ_pct_of_max = (circ_supply / max_supply) * 100
                         st.progress(int(circ_pct_of_max), text=f"{circ_pct_of_max:.1f}% of Max Supply Circulating")
                     
                     # Simple Pie Chart for Supply (if multiple values exist)
                     if len(supply_data) > 1:
                         # Use only Circulating vs (Total - Circulating) or (Max - Circulating) for pie
                         pie_data = {}
                         if circ_supply is not None: pie_data['Circulating'] = circ_supply
                         
                         non_circulating_label = "Non-Circulating"
                         if total_supply is not None and circ_supply is not None and total_supply > circ_supply:
                              pie_data[non_circulating_label] = total_supply - circ_supply
                         elif max_supply is not None and circ_supply is not None and max_supply > circ_supply:
                              pie_data[non_circulating_label] = max_supply - circ_supply
                              non_circulating_label = "Locked/Unreleased" # Better label if max exists
                         
                         if len(pie_data) > 1:
                             supply_pie_df = pd.DataFrame(pie_data.items(), columns=['Category', 'Amount'])
                             fig_supply_pie = px.pie(supply_pie_df, values='Amount', names='Category', title='Supply Distribution',
                                                    height=200, hole=0.4)
                             fig_supply_pie.update_layout(showlegend=False, margin=dict(l=0,r=0,t=30,b=0))
                             fig_supply_pie.update_traces(textinfo='percent+label')
                             st.plotly_chart(fig_supply_pie, use_container_width=True)

        # --- Tab 2: Charts ---
        with tab2:
            st.subheader(f"{selected_coin_name} Price Chart ({days_history} Days)")
            
            if chart_type == "Line Chart":
                # Fetch historical data (Price and Volume) using utils function
                hist_df = utils.get_historical_data(selected_coin_id, currency, days=days_history)
                
                if not hist_df.empty and 'price' in hist_df.columns and 'volume' in hist_df.columns:
                    # Create figure with secondary y-axis
                    fig = make_subplots(rows=1, cols=1, specs=[[{"secondary_y": True}]])

                    # Add Price trace
                    fig.add_trace(
                        go.Scatter(x=hist_df['date'], y=hist_df['price'], name=f"Price ({currency_upper})"),
                        secondary_y=False,
                    )

                    # Add Volume trace
                    fig.add_trace(
                        go.Bar(x=hist_df['date'], y=hist_df['volume'], name=f"Volume ({currency_upper})", opacity=0.4),
                        secondary_y=True,
                    )

                    # Set titles and labels
                    fig.update_layout(
                        title_text=f"{selected_coin_name} Price and Volume ({currency_upper})",
                        xaxis_title="Date",
                        legend_title="Metric"
                    )
                    fig.update_yaxes(title_text="<b>Price ({currency_upper})</b>", secondary_y=False)
                    fig.update_yaxes(title_text="<b>Volume ({currency_upper})</b>", secondary_y=True, showgrid=False)

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Could not fetch or process historical price/volume data for the line chart.")

            elif chart_type == "Candlestick Chart":
                # Fetch OHLC data using utils function
                ohlc_df = utils.get_ohlc_data(selected_coin_id, currency, days=days_history)
                # Fetch volume data separately for overlay (OHLC endpoint doesn't include volume)
                hist_df_vol = utils.get_historical_data(selected_coin_id, currency, days=days_history)

                if not ohlc_df.empty and 'open' in ohlc_df.columns:
                    # Create figure with secondary y-axis
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                       vertical_spacing=0.1, row_heights=[0.7, 0.3]) # Allocate more space for price

                    # Add Candlestick trace to the first row
                    fig.add_trace(go.Candlestick(x=ohlc_df['date'],
                                    open=ohlc_df['open'], high=ohlc_df['high'],
                                    low=ohlc_df['low'], close=ohlc_df['close'],
                                    name="Price (OHLC)"), row=1, col=1)

                    # Add Volume trace to the second row
                    if not hist_df_vol.empty and 'volume' in hist_df_vol.columns:
                        fig.add_trace(go.Bar(x=hist_df_vol['date'], y=hist_df_vol['volume'], name="Volume", marker_color='rgba(100,149,237,0.5)'), row=2, col=1)
                         # Update y-axis title for volume
                        fig.update_yaxes(title_text="Volume", row=2, col=1)
                    else:
                        st.warning("Volume data could not be fetched for candlestick overlay.")

                    # Update layout
                    fig.update_layout(
                        title=f"{selected_coin_name} Candlestick Chart ({currency_upper})",
                        xaxis_title="Date",
                        yaxis_title=f"Price ({currency_upper})",
                        xaxis_rangeslider_visible=False, # Hide rangeslider for cleaner look
                        height=600 # Increase height for two rows
                    )
                    # Remove gap between rows
                    fig.update_layout(xaxis2_showticklabels=True) # Ensure date labels show on bottom chart

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Could not fetch or process OHLC data for the candlestick chart.")


        # --- Tab 3: Info & Links ---
        with tab3:
            # Description
            st.subheader("About")
            description = details.get('description', {}).get('en', 'No description available.')
            with st.expander("Read Description...", expanded=False):
                import re
                # Basic regex to remove HTML tags - might need refinement for complex HTML
                clean_desc = re.sub('<[^<]+?>', '', description) if description else 'No description available.'
                st.markdown(clean_desc)

            st.divider()

            # Links
            st.subheader("Official Links")
            links = details.get('links', {})
            # Safely get first homepage link if list exists
            homepage = links.get('homepage', [None])[0] 
            # Get up to 3 blockchain explorers, filtering out empty strings
            blockchain_explorers = [url for url in links.get('blockchain_site', []) if url][:3] 
            twitter_username = links.get('twitter_screen_name', None)
            subreddit_url = links.get('subreddit_url', None)
            
            link_cols = st.columns(4) # Create columns for buttons
            if homepage: link_cols[0].link_button("Homepage", homepage)
            if twitter_username: link_cols[1].link_button("Twitter", f"https://twitter.com/{twitter_username}")
            if subreddit_url: link_cols[2].link_button("Reddit", subreddit_url)
            # Use the 4th column for an expander if explorers exist
            if blockchain_explorers:
                 with link_cols[3].expander("Explorers"):
                     for i, explorer in enumerate(blockchain_explorers):
                         st.link_button(f"Explorer {i+1}", explorer)
                         
            # Display other links if available
            other_links = {
                 "Official Forum": links.get('official_forum_url', [None])[0],
                 "Chat": links.get('chat_url', [None])[0],
                 "Announcement": links.get('announcement_url', [None])[0],
                 # Add more as needed, e.g., Facebook, Telegram
            }
            other_links_filtered = {name: url for name, url in other_links.items() if url}
            if other_links_filtered:
                 st.divider()
                 st.markdown("**Other Links:**")
                 for name, url in other_links_filtered.items():
                     st.link_button(name, url)

    else:
        st.error(f"Could not retrieve details for the selected coin ID: {selected_coin_id}. The coin might be invalid or the API unavailable.")

elif not coin_map:
     st.error("Application cannot function without the coin list. Please check API status or try again later.")
elif selected_coin_id is None and selected_coin_name:
    # Handle case where selected name didn't map to an ID (should be rare with current setup)
    st.error(f"Could not find a valid ID for the selected coin: {selected_coin_name}")
else: # No coin selected yet, and coin_map was loaded successfully
    st.info("⬅️ Please select a coin from the sidebar to view its details.") 