import streamlit as st
import pandas as pd
import requests
import time # To avoid hitting API rate limits too quickly
import plotly.express as px # Import Plotly Express

# --- Page Config ---
st.set_page_config(page_title="Portfolio Management", page_icon="💼", layout="wide")

st.title("💼 Portfolio Management")
st.markdown("Track your cryptocurrency holdings.")

# --- Helper Functions (Adapt from other pages or create new ones) ---

# Placeholder for CoinGecko API base URL
CG_BASE_URL = "https://api.coingecko.com/api/v3"

# Cache coin list (similar to other pages)
@st.cache_data(ttl=3600 * 6) # Cache for 6 hours
def get_coin_list():
    url = f"{CG_BASE_URL}/coins/list?include_platform=false"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Create a mapping of display name (lowercase) to coin ID
        # Example: {'bitcoin': 'bitcoin', 'ethereum': 'ethereum'}
        return {coin['name'].lower(): coin['id'] for coin in data}
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching coin list: {e}")
        return {}
    except Exception as e:
        st.error(f"An error occurred processing the coin list: {e}")
        return {}

# Function to get current prices for a list of coin IDs
@st.cache_data(ttl=60) # Cache prices for 60 seconds
def get_current_prices(coin_ids, currency='usd'):
    if not coin_ids:
        return {}
    
    ids_string = ",".join(coin_ids)
    url = f"{CG_BASE_URL}/simple/price?ids={ids_string}&vs_currencies={currency}"
    
    prices = {}
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Extract price for each coin_id
        for coin_id in coin_ids:
            prices[coin_id] = data.get(coin_id, {}).get(currency)
        return prices
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 429:
            st.warning(f"Rate limit hit fetching prices. Please wait.")
        else:
            st.warning(f"Could not fetch prices (HTTP Error {response.status_code}).")
        return prices # Return potentially partial data or empty dict
    except requests.exceptions.RequestException as e:
        st.warning(f"Network error fetching prices: {e}")
        return prices
    except Exception as e:
        st.error(f"An unexpected error occurred fetching prices: {e}")
        return prices

# --- Initialize Session State ---
if 'portfolio' not in st.session_state:
    # Structure: List of dictionaries
    # Example: [{'id': 'bitcoin', 'name': 'Bitcoin', 'quantity': 1.5, 'purchase_price': 20000}, ...]
    st.session_state.portfolio = [] 

# --- Load Coin Data ---
coin_map = get_coin_list()
if not coin_map:
    st.error("Failed to load coin list from CoinGecko. Cannot proceed.")
    st.stop()

# Create list of coin names for selectbox, sorted alphabetically
# Ensure names are capitalized for display
all_coin_names_display = sorted([name.title() for name in coin_map.keys()])

# --- Input Section ---
st.header("Add New Holding")

with st.form("add_holding_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_coin_name = st.selectbox(
            "Select Coin", 
            options=all_coin_names_display, 
            index=0, # Default to first coin alphabetically
            key="portfolio_coin_select"
        )
    with col2:
        quantity = st.number_input("Quantity", min_value=0.0, format="%f", step=0.01, key="portfolio_quantity")
    with col3:
        purchase_price = st.number_input("Purchase Price (USD, Optional)", min_value=0.0, value=0.0, format="%.2f", step=0.01, key="portfolio_purchase_price")
        
    submitted = st.form_submit_button("Add to Portfolio")
    
    if submitted:
        if selected_coin_name and quantity > 0:
            # Find the coin ID from the selected display name
            coin_id = coin_map.get(selected_coin_name.lower())
            if coin_id:
                # Check if coin already exists, if so, update quantity (or add as separate entry - let's add as separate for now)
                # Simple approach: always append
                new_holding = {
                    'id': coin_id,
                    'name': selected_coin_name, # Store the display name
                    'quantity': quantity,
                    'purchase_price': purchase_price if purchase_price > 0 else None # Store None if price is 0 or less
                }
                st.session_state.portfolio.append(new_holding)
                st.success(f"Added {quantity} {selected_coin_name} to portfolio.")
            else:
                st.error(f"Could not find ID for {selected_coin_name}. Holding not added.")
        elif not selected_coin_name:
            st.error("Please select a coin.")
        else: # quantity is 0 or less
            st.error("Quantity must be greater than zero.")

# --- Display Portfolio ---
st.header("Current Portfolio")

if not st.session_state.portfolio:
    st.info("Your portfolio is empty. Add holdings using the form above.")
else:
    # Convert portfolio list to DataFrame for easier processing
    portfolio_df = pd.DataFrame(st.session_state.portfolio)
    
    # Get unique coin IDs to fetch prices
    portfolio_coin_ids = portfolio_df['id'].unique().tolist()
    
    # Fetch current prices
    current_prices = get_current_prices(portfolio_coin_ids, currency='usd')
    
    # Add current price and value to DataFrame
    portfolio_df['current_price'] = portfolio_df['id'].map(current_prices)
    
    # Handle cases where price fetching failed for some coins
    portfolio_df['current_price'] = pd.to_numeric(portfolio_df['current_price'], errors='coerce') # Ensure numeric, turn errors into NaN
    portfolio_df['current_value'] = portfolio_df['quantity'] * portfolio_df['current_price']
    
    # Calculate P/L if purchase price is available
    portfolio_df['pnl'] = None # Initialize P/L column
    has_purchase_price = pd.notna(portfolio_df['purchase_price']) & pd.notna(portfolio_df['current_value']) & (portfolio_df['purchase_price'] > 0)
    
    # Calculate P/L only where purchase price exists and current value is known
    portfolio_df.loc[has_purchase_price, 'pnl'] = (portfolio_df['current_price'] - portfolio_df['purchase_price']) * portfolio_df['quantity']
    
    # --- Display Summary Metrics ---
    total_value = portfolio_df['current_value'].sum()
    total_pnl = portfolio_df['pnl'].sum() if portfolio_df['pnl'].notna().any() else None # Sum PNL only if there are non-NaN values

    st.subheader("Portfolio Summary")
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Total Portfolio Value (USD)", f"${total_value:,.2f}" if pd.notna(total_value) else "N/A")
    if total_pnl is not None:
        col_m2.metric("Total Profit/Loss (USD)", f"${total_pnl:,.2f}")
    else:
        col_m2.metric("Total Profit/Loss (USD)", "N/A (Enter purchase prices)")
        
    st.divider()
    
    # --- Add Visualizations ---
    st.subheader("Portfolio Visualizations")
    
    # Filter data for charts (remove rows with missing values needed for each chart)
    pie_chart_df = portfolio_df.dropna(subset=['current_value'])
    pnl_chart_df = portfolio_df.dropna(subset=['pnl'])
    
    col_v1, col_v2 = st.columns(2)
    
    with col_v1:
        if not pie_chart_df.empty:
            fig_dist = px.pie(pie_chart_df, 
                            names='name', 
                            values='current_value', 
                            title='Portfolio Value Distribution by Coin', 
                            hole=.3) # Donut chart style
            fig_dist.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info("Add holdings with current value to see distribution chart.")

    with col_v2:
        if not pnl_chart_df.empty:
            # Add color based on P/L sign
            pnl_chart_df['pnl_color'] = pnl_chart_df['pnl'].apply(lambda x: 'Positive' if x >= 0 else 'Negative')
            
            fig_pnl = px.bar(pnl_chart_df, 
                           x='name', 
                           y='pnl', 
                           title='Profit/Loss per Holding',
                           color='pnl_color', # Color bars
                           color_discrete_map={'Positive': 'green', 'Negative': 'red'}, # Define colors
                           labels={'pnl': 'Profit/Loss (USD)', 'name': 'Coin'})
            fig_pnl.update_layout(showlegend=False) # Hide legend as colors are direct
            st.plotly_chart(fig_pnl, use_container_width=True)
        else:
            st.info("Add holdings with purchase prices to see P/L chart.")
            
    st.divider()

    # --- Display Detailed Table ---
    st.subheader("Holdings Details")
    
    # Format columns for display
    display_df = portfolio_df[[
        'name', 
        'quantity', 
        'purchase_price', 
        'current_price', 
        'current_value', 
        'pnl'
    ]].copy() # Work on a copy
    
    st.dataframe(display_df.style
        .format({
            'quantity': '{:,.6f}'.format,
            'purchase_price': '${:,.2f}'.format,
            'current_price': '${:,.2f}'.format,
            'current_value': '${:,.2f}'.format,
            'pnl': '${:,.2f}'.format,
        }, na_rep="N/A") # Show N/A for missing values
        .highlight_null(color='rgba(150, 150, 150, 0.1)') # Use 'color' instead of 'null_color'
        # Check for non-null before comparing in applymap
        .map(lambda x: ('color: green' if x > 0 else ('color: red' if x < 0 else None)) if pd.notna(x) else None, subset=['pnl']), 
        use_container_width=True
    )
    
    # --- Add a way to clear the portfolio (optional) ---
    if st.button("Clear Portfolio", key="clear_portfolio"):
        st.session_state.portfolio = []
        st.rerun() # Rerun the script to reflect the cleared state immediately
        
# --- Add Disclaimer ---
st.sidebar.markdown("--- ")
st.sidebar.warning("**Disclaimer:** Portfolio data is stored only for your current browser session. It will be lost when you close this tab.")
st.sidebar.warning("Cryptocurrency prices are highly volatile. Data provided by CoinGecko.") 