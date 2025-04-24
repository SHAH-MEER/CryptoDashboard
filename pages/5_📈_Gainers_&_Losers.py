import streamlit as st
import requests
import pandas as pd
import plotly.express as px # Import Plotly Express

st.set_page_config(page_title="Gainers & Losers", page_icon="💹", layout="wide")

st.title("💹 Top 24h Gainers & Losers")

# --- Helper Function (Similar to Dashboard's get_top_coins) ---
@st.cache_data(ttl=180) # Cache for 3 minutes
def get_market_data(currency, num_coins=250):
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page={num_coins}&page=1&sparkline=false&price_change_percentage=24h"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Select and rename columns for clarity
        df = pd.DataFrame(data)[[
            'name', 'symbol', 'current_price', 
            'price_change_percentage_24h', 'total_volume'
        ]]
        df.rename(columns={
            'price_change_percentage_24h': 'change_24h',
            'current_price': 'price'
        }, inplace=True)
        # Ensure numeric types
        df['change_24h'] = pd.to_numeric(df['change_24h'], errors='coerce')
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce')
        df = df.dropna(subset=['change_24h']) # Remove coins with missing change data
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching market data: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred processing market data: {e}")
        return pd.DataFrame()

# --- Sidebar --- 
st.sidebar.header("⚙️ Options")
currency = st.sidebar.selectbox(
    "Select Currency", 
    ["usd", "eur", "gbp", "jpy", "btc", "eth"], 
    key="gl_currency"
)
num_results = st.sidebar.slider("Number of Top Gainers/Losers to Show", 5, 50, 10, key="gl_num_results")

# --- Main Page ---
currency_upper = currency.upper()

market_df = get_market_data(currency, num_coins=250) # Fetch top 250 by market cap

if not market_df.empty:
    # --- Identify Top Gainer & Loser --- 
    # Drop potential NaNs before finding idxmax/idxmin
    market_df_clean = market_df.dropna(subset=['change_24h'])
    if not market_df_clean.empty:
        top_gainer = market_df_clean.loc[market_df_clean['change_24h'].idxmax()]
        top_loser = market_df_clean.loc[market_df_clean['change_24h'].idxmin()]
    else:
        top_gainer = None
        top_loser = None

    # --- Display Top Highlights --- 
    if top_gainer is not None and top_loser is not None:
        st.subheader("Top Movers (24h)")
        col_hl1, col_hl2 = st.columns(2)
        with col_hl1:
            st.metric(
                label=f"🔥 Biggest Gainer: {top_gainer['name']} ({top_gainer['symbol'].upper()})", 
                value=f"{top_gainer['price']:,.4f} {currency_upper}", 
                delta=f"{top_gainer['change_24h']:.2f}%"
            )
        with col_hl2:
            st.metric(
                label=f"🧊 Biggest Loser: {top_loser['name']} ({top_loser['symbol'].upper()})", 
                value=f"{top_loser['price']:,.4f} {currency_upper}", 
                delta=f"{top_loser['change_24h']:.2f}%"
            )
        st.divider()

    st.markdown(f"Showing top **{num_results}** gainers and losers from the top 250 cryptocurrencies by market cap, compared against **{currency_upper}**.")
    st.markdown("_")
    
    # Sort dataframes for tables/charts
    gainers_df = market_df.sort_values(by='change_24h', ascending=False).head(num_results)
    losers_df = market_df.sort_values(by='change_24h', ascending=True).head(num_results)

    # Create columns for layout
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"🔥 Top {num_results} Gainers (24h)")
        st.dataframe(gainers_df.style.format({
            'price': '{:,.4f}'.format,
            'change_24h': '+{:.2f}%'.format, # Add plus sign for gainers
            'total_volume': '{:,.0f}'.format
        }).highlight_max(subset=['change_24h'], color='lightgreen'), 
        hide_index=True,
        column_config={
             "name": "Coin",
             "symbol": "Symbol",
             "price": st.column_config.NumberColumn(f"Price ({currency_upper})"),
             "change_24h": st.column_config.NumberColumn("24h Change"),
             "total_volume": st.column_config.NumberColumn(f"24h Volume ({currency_upper})")
        },
        use_container_width=True)
        
        # Display Gainer Bar Chart
        fig_gainers = px.bar(gainers_df.sort_values(by='change_24h', ascending=True), # Sort for better bar chart visual
                               x='change_24h', 
                               y='name', 
                               orientation='h',
                               title=f"Top {num_results} Gainers (% Change)",
                               labels={'name':'Coin', 'change_24h':'24h Change (%)'},
                               text='change_24h')
        fig_gainers.update_traces(texttemplate='%{text:.2f}%', textposition='outside', marker_color='#2ca02c') # Green color
        fig_gainers.update_layout(yaxis_title=None, xaxis_title="24h Change (%)")
        st.plotly_chart(fig_gainers, use_container_width=True)
        
        # Display Gainer Volume Bar Chart
        st.markdown("_") # Spacer
        fig_gainers_vol = px.bar(gainers_df.sort_values(by='total_volume', ascending=False), # Sort by volume
                               x='total_volume', 
                               y='name', 
                               orientation='h',
                               title=f"Top {num_results} Gainers (24h Volume)",
                               labels={'name':'Coin', 'total_volume':f'24h Volume ({currency_upper})'},
                               text='total_volume')
        fig_gainers_vol.update_traces(texttemplate='%{text:,.0f}', textposition='outside', marker_color='#1f77b4') # Blue color
        fig_gainers_vol.update_layout(yaxis_title=None, xaxis_title=f"24h Volume ({currency_upper})")
        st.plotly_chart(fig_gainers_vol, use_container_width=True)

    with col2:
        st.subheader(f"🧊 Top {num_results} Losers (24h)")
        st.dataframe(losers_df.style.format({
             'price': '{:,.4f}'.format,
             'change_24h': '{:.2f}%'.format, # Losers are already negative
             'total_volume': '{:,.0f}'.format
         }).highlight_min(subset=['change_24h'], color='#FFCCCB'), # Light red
         hide_index=True,
         column_config={
              "name": "Coin",
              "symbol": "Symbol",
              "price": st.column_config.NumberColumn(f"Price ({currency_upper})"),
              "change_24h": st.column_config.NumberColumn("24h Change"),
              "total_volume": st.column_config.NumberColumn(f"24h Volume ({currency_upper})")
         },
         use_container_width=True)

        # Display Loser Bar Chart
        fig_losers = px.bar(losers_df.sort_values(by='change_24h', ascending=False), # Sort for better bar chart visual
                              x='change_24h', 
                              y='name', 
                              orientation='h',
                              title=f"Top {num_results} Losers (% Change)",
                              labels={'name':'Coin', 'change_24h':'24h Change (%)'},
                              text='change_24h')
        fig_losers.update_traces(texttemplate='%{text:.2f}%', textposition='outside', marker_color='#d62728') # Red color
        fig_losers.update_layout(
             yaxis_title=None, 
             xaxis_title="24h Change (%)",
             yaxis=dict(side='left') # Force y-axis labels to the left
        )
        st.plotly_chart(fig_losers, use_container_width=True)
        
        # Display Loser Volume Bar Chart
        st.markdown("_") # Spacer
        fig_losers_vol = px.bar(losers_df.sort_values(by='total_volume', ascending=False), # Sort by volume
                              x='total_volume', 
                              y='name', 
                              orientation='h',
                              title=f"Top {num_results} Losers (24h Volume)",
                              labels={'name':'Coin', 'total_volume':f'24h Volume ({currency_upper})'},
                              text='total_volume')
        fig_losers_vol.update_traces(texttemplate='%{text:,.0f}', textposition='outside', marker_color='#9467bd') # Purple color
        fig_losers_vol.update_layout(yaxis_title=None, xaxis_title=f"24h Volume ({currency_upper})")
        st.plotly_chart(fig_losers_vol, use_container_width=True)

    # --- Combined Scatter Plot --- 
    st.divider()
    st.subheader("Gainers & Losers: 24h Change vs. Volume")
    
    # Combine gainers and losers for scatter plot
    scatter_df = pd.concat([gainers_df, losers_df])
    scatter_df['type'] = ['Gainer'] * len(gainers_df) + ['Loser'] * len(losers_df)

    if not scatter_df.empty:
        fig_scatter_gl = px.scatter(
            scatter_df,
            x='change_24h',
            y='total_volume',
            color='type',
            size='price',  # Size bubbles by current price
            hover_name='name',
            hover_data=['symbol', 'price', 'change_24h', 'total_volume'],
            color_discrete_map={'Gainer': 'green', 'Loser': 'red'},
            log_y=True, # Volume can vary greatly, log scale helps
            title=f"Top {num_results} Gainers & Losers: Change vs Volume (Size by Price)",
            labels={
                'change_24h': '24h Change (%)',
                'total_volume': f'24h Volume ({currency_upper}) (Log Scale)',
                'price': f'Price ({currency_upper})',
                'type': 'Category'
            }
        )
        fig_scatter_gl.update_layout(yaxis_title=f'24h Volume ({currency_upper}) (Log Scale)', xaxis_title='24h Change (%)')
        st.plotly_chart(fig_scatter_gl, use_container_width=True)
    else:
        st.info("Could not generate scatter plot for gainers/losers.")

else:
    st.warning("Could not fetch market data. Check API status or try again later.") 