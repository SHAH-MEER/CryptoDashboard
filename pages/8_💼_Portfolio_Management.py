import streamlit as st
import pandas as pd
import requests
import time # To avoid hitting API rate limits too quickly
import plotly.express as px
import utils # Import the utility module

# --- Page Config ---
st.set_page_config(page_title="Portfolio Management", page_icon="💼", layout="wide")

st.title("💼 Portfolio Management")
st.markdown("Track your cryptocurrency holdings.")

# --- Helper Functions (Adapt from other pages or create new ones) ---
# Functions moved to utils.py:
# get_coin_list()
# get_current_prices(coin_ids, currency='usd')

# --- Initialize Session State ---
if 'portfolio' not in st.session_state:
    # Structure: List of dictionaries
    # Example: [{'id': 'bitcoin', 'name': 'Bitcoin', 'quantity': 1.5, 'purchase_price': 20000}, ...]
    st.session_state.portfolio = [] 

# --- Load Coin Data ---
# Call function from utils module
coin_map = utils.get_coin_list()

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
            index=0 if all_coin_names_display else None, # Default to first coin alphabetically if list exists
            key="portfolio_coin_select"
        )
    with col2:
        quantity = st.number_input("Quantity", min_value=0.0, format="%.8f", step=0.01, key="portfolio_quantity") # Increased precision
    with col3:
        purchase_price = st.number_input("Purchase Price (USD, Optional)", min_value=0.0, value=0.0, format="%.2f", step=0.01, key="portfolio_purchase_price")
        
    submitted = st.form_submit_button("Add to Portfolio")
    if submitted and selected_coin_name and quantity > 0:
        coin_id = coin_map.get(selected_coin_name.lower())
        if coin_id:
            # Check if coin already exists in portfolio to update quantity
            found = False
            for holding in st.session_state.portfolio:
                if holding['id'] == coin_id:
                    holding['quantity'] += quantity
                    # Optionally update average purchase price (more complex logic)
                    # holding['purchase_price'] = calculate_new_avg_price(...) 
                    st.success(f"Updated quantity for {selected_coin_name}.")
                    found = True
                    break
            if not found:
                st.session_state.portfolio.append({
                    'id': coin_id,
                    'name': selected_coin_name, # Store Title Case Name
                    'quantity': quantity,
                    'purchase_price': purchase_price if purchase_price > 0 else None # Store None if not provided
                })
                st.success(f"Added {quantity} {selected_coin_name} to your portfolio.")
        else:
            st.error(f"Could not find ID for {selected_coin_name}")
    elif submitted:
        st.warning("Please select a coin and enter a quantity greater than 0.")

# --- Display Portfolio --- 
st.divider()
st.header("Your Portfolio")

if not st.session_state.portfolio:
    st.info("Your portfolio is empty. Add holdings using the form above.")
elif not coin_map: # Check again in case API failed after initial load
    st.error("Cannot display portfolio values because the coin list failed to load.")
else:
    # Create DataFrame from session state
    portfolio_df = pd.DataFrame(st.session_state.portfolio)

    # Get unique coin IDs from portfolio
    portfolio_coin_ids = portfolio_df['id'].unique().tolist()

    # Fetch current prices for these coins using utils function
    if portfolio_coin_ids:
        current_prices = utils.get_current_prices(portfolio_coin_ids, currency='usd')
    else:
        current_prices = {}
        
    # Add current price and value to the DataFrame
    portfolio_df['current_price_usd'] = portfolio_df['id'].map(current_prices).fillna(0)
    portfolio_df['current_value_usd'] = portfolio_df['quantity'] * portfolio_df['current_price_usd']
    
    # Calculate total purchase value (if purchase prices are available)
    portfolio_df['total_purchase_cost_usd'] = portfolio_df['quantity'] * portfolio_df['purchase_price'].fillna(0)
    
    # Calculate Profit/Loss
    portfolio_df['pnl_usd'] = portfolio_df['current_value_usd'] - portfolio_df['total_purchase_cost_usd']
    # Avoid division by zero if purchase cost is 0
    portfolio_df['pnl_percent'] = (
        (portfolio_df['pnl_usd'] / portfolio_df['total_purchase_cost_usd'] * 100)
        .where(portfolio_df['total_purchase_cost_usd'] != 0, other=0) # Assign 0% if cost is 0
        .fillna(0) # Fill NaN (e.g., if purchase price was None/0)
    )

    # --- Display Summary Metrics ---
    total_value = portfolio_df['current_value_usd'].sum()
    total_purchase_cost = portfolio_df['total_purchase_cost_usd'].sum()
    total_pnl = portfolio_df['pnl_usd'].sum()
    total_pnl_percent = (total_pnl / total_purchase_cost * 100) if total_purchase_cost else 0

    st.subheader("Portfolio Summary")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Total Current Value (USD)", f"${total_value:,.2f}")
    metric_cols[1].metric("Total Profit/Loss (USD)", f"${total_pnl:,.2f}")
    metric_cols[2].metric("Total P/L (%)", f"{total_pnl_percent:.2f}%")

    st.divider()

    # --- Display Holdings Table ---
    st.subheader("Detailed Holdings")
    # Add remove button column
    portfolio_df['Remove'] = False 
    
    edited_df = st.data_editor(
        portfolio_df,
        column_config={
            "id": None, # Hide the ID column
            "name": "Coin",
            "quantity": st.column_config.NumberColumn("Quantity", format="%.8f"),
            "purchase_price": st.column_config.NumberColumn("Avg. Purchase Price (USD)", format="%.2f"),
            "total_purchase_cost_usd": st.column_config.NumberColumn("Total Cost (USD)", format="%.2f"),
            "current_price_usd": st.column_config.NumberColumn("Current Price (USD)", format="%.4f"),
            "current_value_usd": st.column_config.NumberColumn("Current Value (USD)", format="%.2f"),
            "pnl_usd": st.column_config.NumberColumn("P/L (USD)", format="%.2f"),
            "pnl_percent": st.column_config.NumberColumn("P/L (%)", format="%.2f%%"),
            "Remove": st.column_config.CheckboxColumn("Remove?")
        },
        key="portfolio_editor",
        hide_index=True,
        use_container_width=True,
        # Allow editing quantity and purchase price
        disabled=["id", "name", "total_purchase_cost_usd", "current_price_usd", "current_value_usd", "pnl_usd", "pnl_percent"]
    )

    # Process removals and updates
    rows_to_remove_indices = edited_df[edited_df['Remove']].index
    if not rows_to_remove_indices.empty:
        # Get original indices from session state before filtering
        original_indices_to_remove = [st.session_state.portfolio[i]['id'] for i in rows_to_remove_indices]
        st.session_state.portfolio = [h for i, h in enumerate(st.session_state.portfolio) if i not in rows_to_remove_indices]
        st.info(f"Removed {len(rows_to_remove_indices)} holding(s). Re-run the page to see changes.")
        st.rerun() # Rerun to update display after removal
    else:
        # Update session state with edited values (quantity, purchase_price)
        # This assumes the index of edited_df matches the session_state list order before removals
        if not edited_df.equals(portfolio_df.drop(columns=['Remove'])): # Check if edits were made (excluding the Remove column)
             updated_portfolio = []
             for index, row in edited_df.iterrows():
                 if index < len(st.session_state.portfolio): # Ensure index is valid
                     # Find the corresponding item in session_state based on ID (more robust)
                     original_item = next((item for item in st.session_state.portfolio if item['id'] == row['id']), None)
                     if original_item:
                         original_item['quantity'] = row['quantity']
                         original_item['purchase_price'] = row['purchase_price']
                         updated_portfolio.append(original_item)
                     else:
                         # This case should ideally not happen if IDs are managed correctly
                         st.warning(f"Could not find original item for ID {row['id']} during update.")
                         # Append the edited row as a fallback? Or skip?
                         # updated_portfolio.append(row.to_dict()) # Example: Appending the edited row
                 else:
                     st.warning(f"Index {index} out of bounds during portfolio update.")
                     
             if updated_portfolio:
                 st.session_state.portfolio = updated_portfolio
                 st.success("Portfolio updated. Re-running...")
                 time.sleep(1) # Brief pause before rerun
                 st.rerun() 

    # --- Visualizations ---
    st.divider()
    st.subheader("Portfolio Allocation")

    if not portfolio_df.empty and portfolio_df['current_value_usd'].sum() > 0:
        fig_pie = px.pie(portfolio_df, values='current_value_usd', names='name',
                         title="Portfolio Allocation by Current Value (USD)",
                         hover_data=['quantity', 'current_price_usd'],
                         labels={'name': 'Coin', 'current_value_usd': 'Value (USD)'})
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Not enough data or zero total value for allocation chart.")

# --- Add Disclaimer ---
st.sidebar.markdown("--- ")
st.sidebar.warning("**Disclaimer:** Portfolio data is stored only for your current browser session. It will be lost when you close this tab.")
st.sidebar.warning("Cryptocurrency prices are highly volatile. Data provided by CoinGecko.") 