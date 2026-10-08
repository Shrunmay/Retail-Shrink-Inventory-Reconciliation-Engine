"""
CTC Loss Prevention Case Dossier Generator
Transforms Kùzu graph anomalies into human-readable investigator reports.
"""

from pathlib import Path
import kuzu
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "kuzu_db"

def get_flagged_syndicate(conn: kuzu.Connection) -> pd.DataFrame:
    """Re-runs the multi-store corridor sweep to isolate the top ORC token."""
    cypher = """
    MATCH (tx:Transaction)-[:Tx_Token]->(tok:Token),
          (tx:Transaction)-[:Tx_Store]->(st:Store),
          (tx:Transaction)-[:Tx_Product]->(prod:Product)
    OPTIONAL MATCH (p:Person)-[:Person_Tx]->(tx:Transaction)
    WHERE tx.transaction_type = 'RETURN' 
      AND tx.is_receipted = false
      AND prod.theft_tier = 'HIGH'
    RETURN 
        tok.id AS payment_token,
        tx.id AS tx_id,
        tx.timestamp AS timestamp,
        st.city AS city,
        st.store_id AS store_id,
        prod.name AS product_name,
        tx.amount AS amount,
        p.id AS loyalty_id
    """
    df = conn.execute(cypher).get_as_df()
    
    # Filter for tokens hitting 3+ stores (Our ORC Corridor Rule)
    if df.empty:
        return pd.DataFrame()
        
    store_counts = df.groupby("payment_token")["store_id"].nunique()
    flagged_tokens = store_counts[store_counts >= 3].index.tolist()
    
    if not flagged_tokens:
        return pd.DataFrame()
        
    # Get the details for the worst offender
    top_token = flagged_tokens[0]
    return df[df["payment_token"] == top_token].sort_values("timestamp")

def generate_report(df: pd.DataFrame) -> str:
    """Formats the DataFrame into a readable LP brief."""
    if df.empty:
        return "No high-risk syndicates detected at this time."

    token = df.iloc[0]["payment_token"]
    total_exposure = df["amount"].sum()
    stores_hit = df["store_id"].nunique()
    start_time = pd.to_datetime(df["timestamp"].min())
    end_time = pd.to_datetime(df["timestamp"].max())
    duration_hours = round((end_time - start_time).total_seconds() / 3600, 1)

    report = []
    report.append("=" * 65)
    report.append(f"🚨 CONFIDENTIAL LP INVESTIGATION DOSSIER 🚨")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 65)
    report.append(f"ALERT: Coordinated Cross-Store Return Fraud (Tender Wash)")
    report.append(f"FLAGGED TOKEN: {token}")
    report.append(f"TOTAL EXPOSURE: ${total_exposure:.2f}")
    report.append(f"PATTERN DURATION: {duration_hours} hours")
    report.append(f"STORES HIT: {stores_hit} distinct locations")
    report.append("-" * 65)
    report.append("TIMELINE OF EVENTS:")
    
    for _, row in df.iterrows():
        loyalty = row["loyalty_id"] if pd.notna(row["loyalty_id"]) else "ANONYMOUS (No Card)"
        report.append(
            f"  [{row['timestamp']}] | {row['city']:<15} | "
            f"${row['amount']:<7.2f} | ID: {loyalty:<15} | Item: {row['product_name'][:25]}..."
        )
        
    report.append("-" * 65)
    report.append("INVESTIGATION RECOMMENDATIONS:")
    report.append("1. Pull CCTV timestamps for the registers associated with these transactions.")
    report.append("2. Initiate physical Cycle Counts for the listed high-theft SKUs at these stores.")
    report.append("3. Flag payment token in POS system to require manager override for future returns.")
    report.append("=" * 65)
    
    return "\n".join(report)

def main():
    db = kuzu.Database(str(DB_PATH))
    conn = kuzu.Connection(db)
    
    syndicate_df = get_flagged_syndicate(conn)
    report_text = generate_report(syndicate_df)
    print(report_text)

if __name__ == "__main__":
    main()