"""
CTC Loss Prevention - Interactive Investigator Dashboard
Serves Kùzu graph anomalies in a Streamlit web application.
"""

import sys
from pathlib import Path
import pandas as pd
import streamlit as st
import kuzu

# Add src to path so we can import our graph logic
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
from src.anomaly.generate_dossier import get_flagged_syndicate

# Set up page config
st.set_page_config(
    page_title="CTC Loss Prevention Dashboard",
    page_icon="🚨",
    layout="wide"
)

# Connect to database
@st.cache_resource
def init_db():
    db_path = BASE_DIR / "kuzu_db"
    db = kuzu.Database(str(db_path))
    return kuzu.Connection(db)

def main():
    st.title("🚨 Canadian Tire Loss Prevention: ORC Radar")
    st.markdown("### Coordinated Cross-Store Return Fraud Alerts")
    
    conn = init_db()
    
    # Fetch the flagged data
    with st.spinner("Traversing property graph for multi-hop anomalies..."):
        df = get_flagged_syndicate(conn)
        
    if df.empty:
        st.success("✅ No high-risk syndicates detected at this time.")
        return

    # Extract key metrics
    token = df.iloc[0]["payment_token"]
    total_exposure = df["amount"].sum()
    stores_hit = df["store_id"].nunique()
    start_time = pd.to_datetime(df["timestamp"].min())
    end_time = pd.to_datetime(df["timestamp"].max())
    duration_hours = round((end_time - start_time).total_seconds() / 3600, 1)

    # Top Metric Cards
    st.error(f"**High-Risk Target Identified:** Payment Token `{token}`")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Financial Exposure", f"${total_exposure:,.2f}")
    col2.metric("Distinct Stores Hit", stores_hit)
    col3.metric("Spree Duration", f"{duration_hours} hours")
    col4.metric("Unreceipted Returns", len(df))

    st.markdown("---")

    # Transaction Timeline Table
    st.markdown("#### 📍 Geographical Transaction Timeline")
    st.markdown("Notice the rapid movement between GTA stores using the same token but avoiding loyalty capture.")
    
    # Clean up the dataframe for display
    display_df = df[["timestamp", "city", "store_id", "product_name", "amount", "loyalty_id"]].copy()
    display_df["loyalty_id"] = display_df["loyalty_id"].fillna("ANONYMOUS")
    display_df["amount"] = display_df["amount"].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    
    # Action Buttons
    st.markdown("#### ⚖️ Investigator Actions")
    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
        if st.button("🚨 Approve Case (Generate Police Brief & Cycle Counts)", type="primary", use_container_width=True):
            st.success(f"Case escalated! Cycle count tasks dispatched to stores {', '.join(df['store_id'].unique())}.")
            
    with action_col2:
        if st.button("✅ Mark as False Positive (Contractor / Legitimate)", use_container_width=True):
            st.info("Token marked as legitimate. Algorithm weights updated.")

if __name__ == "__main__":
    main()