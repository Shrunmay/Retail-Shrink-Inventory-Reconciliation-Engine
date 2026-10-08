
"""
CTC Fraud Analytics: ORC Detection Engine
Compatible with Kuzu 0.11.3.

Patterns:
1. Shared payment tokens across distinct loyalty identities.
2. Unreceipted returns involving high-theft products across stores.
3. Transaction-level investigation of a flagged token.
"""

from pathlib import Path

import kuzu
import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

DB_PATH = Path(r"E:\ctc-retail-fraud-graph\kuzu_db")

MIN_STORES = 3


# ============================================================
# 2. DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Open the existing Kuzu database.

    Do not use Path.is_dir() here: the existing database at
    DB_PATH was successfully opened by Kuzu 0.11.3.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database path not found: {DB_PATH}\n"
            "Run the graph construction script first."
        )

    db = kuzu.Database(str(DB_PATH))
    conn = kuzu.Connection(db)

    return db, conn


# ============================================================
# 3. DATABASE DIAGNOSTICS
# ============================================================

def inspect_graph(conn):
    """Print node and relationship counts to verify ingestion."""

    print("\n--- GRAPH DATA QUALITY CHECK ---")

    checks = {
        "Person nodes": "MATCH (n:Person) RETURN count(n)",
        "Token nodes": "MATCH (n:Token) RETURN count(n)",
        "Transaction nodes": (
            "MATCH (n:Transaction) RETURN count(n)"
        ),
        "Store nodes": "MATCH (n:Store) RETURN count(n)",
        "Product nodes": "MATCH (n:Product) RETURN count(n)",
        "Person_Tx edges": (
            "MATCH (:Person)-[r:Person_Tx]->(:Transaction) "
            "RETURN count(r)"
        ),
        "Tx_Token edges": (
            "MATCH (:Transaction)-[r:Tx_Token]->(:Token) "
            "RETURN count(r)"
        ),
        "Tx_Store edges": (
            "MATCH (:Transaction)-[r:Tx_Store]->(:Store) "
            "RETURN count(r)"
        ),
        "Tx_Product edges": (
            "MATCH (:Transaction)-[r:Tx_Product]->(:Product) "
            "RETURN count(r)"
        ),
    }

    for label, query in checks.items():
        result = conn.execute(query)
        count = result.get_next()[0]
        print(f"{label:<24} {count:>10,}")


# ============================================================
# 4. PATTERN 1: SHARED TOKEN ACROSS IDENTITIES
# ============================================================

def query_shared_tokens_multi_identity(conn):
    """
    Identify tokens used by distinct Person nodes.

    Counts distinct transactions per person for each token/person pair.
    A shared token is an investigation lead, not proof of fraud.
    """

    print("\n--- PATTERN 1: SHARED IDENTITY TOKENS ---")

    cypher = """
    MATCH
        (p1:Person)-[:Person_Tx]->(tx1:Transaction)
            -[:Tx_Token]->(tok:Token)
            <-[:Tx_Token]-(tx2:Transaction)
            <-[:Person_Tx]-(p2:Person)
    WHERE p1.id < p2.id
    RETURN
        tok.id AS payment_token,
        p1.id AS person_1,
        p2.id AS person_2,
        COUNT(DISTINCT tx1.id) AS person_1_transactions,
        COUNT(DISTINCT tx2.id) AS person_2_transactions
    ORDER BY person_1_transactions DESC
    """

    return conn.execute(cypher).get_as_df()


# ============================================================
# 5. PATTERN 2: MULTI-STORE RETURN CORRIDOR
# ============================================================

def query_multi_store_unreceipted_returns(conn):
    """
    Find tokens linked to unreceipted returns involving high-theft
    products across at least MIN_STORES distinct stores.

    Fetch transaction-level rows first. Calculate exposure using
    distinct transaction IDs in pandas so multiple product edges
    do not multiply transaction amounts.
    """

    print("\n--- PATTERN 2: MULTI-STORE RETURN ACTIVITY ---")

    cypher = """
    MATCH
        (tx:Transaction)-[:Tx_Token]->(tok:Token),
        (tx)-[:Tx_Store]->(st:Store),
        (tx)-[:Tx_Product]->(prod:Product)
    WHERE
        tx.transaction_type = 'RETURN'
        AND tx.is_receipted = false
        AND prod.theft_tier = 'HIGH'
    RETURN
        tok.id AS payment_token,
        tx.id AS transaction_id,
        tx.amount AS amount,
        st.store_id AS store_id,
        prod.sku AS sku
    """

    detail_df = conn.execute(cypher).get_as_df()

    columns = [
        "payment_token",
        "distinct_stores_hit",
        "total_unreceipted_returns",
        "total_return_amount",
        "distinct_high_theft_skus",
    ]

    if detail_df.empty:
        return pd.DataFrame(columns=columns)

    # One row per token/transaction for amount calculation.
    # Multiple product/store edges must not multiply tx.amount.
    transaction_df = detail_df.drop_duplicates(
        subset=["payment_token", "transaction_id"]
    )

    exposure = (
        transaction_df.groupby("payment_token", dropna=False)
        .agg(
            total_unreceipted_returns=("transaction_id", "nunique"),
            total_return_amount=("amount", "sum"),
        )
        .reset_index()
    )

    # Count distinct stores and high-theft SKUs separately.
    activity = (
        detail_df.groupby("payment_token", dropna=False)
        .agg(
            distinct_stores_hit=("store_id", "nunique"),
            distinct_high_theft_skus=("sku", "nunique"),
        )
        .reset_index()
    )

    summary = activity.merge(
        exposure,
        on="payment_token",
        how="left",
    )

    # Flag tokens spanning at least MIN_STORES stores.
    summary = summary[
        summary["distinct_stores_hit"] >= MIN_STORES
    ].copy()

    summary["total_return_amount"] = pd.to_numeric(
        summary["total_return_amount"],
        errors="coerce",
    ).round(2)

    return (
        summary[columns]
        .sort_values(
            by="total_return_amount",
            ascending=False,
            na_position="last",
        )
        .reset_index(drop=True)
    )


# ============================================================
# 6. PATTERN 3: FLAGGED TOKEN INVESTIGATION
# ============================================================

def query_full_syndicate_cluster(conn, token_id):
    """
    Retrieve all transactions associated with a flagged token,
    including linked identities, stores, and products.

    Returns the token's connected transaction details, not every
    possible multi-hop connection in the entire graph.
    """

    print(f"\n--- PATTERN 3: TOKEN INVESTIGATION: {token_id} ---")

    cypher = """
    MATCH (tx:Transaction)-[:Tx_Token]->(tok:Token)
    WHERE tok.id = $token_id

    OPTIONAL MATCH (p:Person)-[:Person_Tx]->(tx)
    OPTIONAL MATCH (tx)-[:Tx_Store]->(st:Store)
    OPTIONAL MATCH (tx)-[:Tx_Product]->(prod:Product)

    RETURN
        tx.id AS tx_id,
        tx.transaction_type AS transaction_type,
        tx.timestamp AS timestamp,
        tx.is_receipted AS is_receipted,
        tx.amount AS amount,
        p.id AS person_loyalty_id,
        st.store_id AS store_id,
        st.city AS city,
        prod.sku AS sku,
        prod.name AS product_name,
        prod.theft_tier AS theft_tier

    ORDER BY timestamp DESC
    """

    result = conn.execute(
        cypher,
        {"token_id": str(token_id)},
    )

    return result.get_as_df()


# ============================================================
# 7. MAIN
# ============================================================

def main():
    print("=" * 65)
    print("CTC FRAUD ENGINE: ORC GRAPH DETECTION")
    print("=" * 65)
    print(f"Database: {DB_PATH}")

    db = None
    conn = None

    try:
        db, conn = get_connection()

        # Check that the graph has been populated.
        inspect_graph(conn)

        # Pattern 1
        shared_df = query_shared_tokens_multi_identity(conn)

        print(
            "\nShared token/person-pair results:",
            len(shared_df),
        )

        if not shared_df.empty:
            print(shared_df.head(10).to_string(index=False))

        # Pattern 2
        corridor_df = query_multi_store_unreceipted_returns(conn)

        print(
            f"\nHigh-risk corridor tokens flagged "
            f"({MIN_STORES}+ stores): {len(corridor_df)}"
        )

        if not corridor_df.empty:
            print(corridor_df.to_string(index=False))

            # Investigate the highest calculated return amount.
            top_token = corridor_df.iloc[0]["payment_token"]

            subgraph_df = query_full_syndicate_cluster(
                conn,
                top_token,
            )

            print(f"\nTransactions linked to token {top_token}:")

            if not subgraph_df.empty:
                print(subgraph_df.to_string(index=False))
            else:
                print("No linked transactions found.")

        print("\nGraph detection completed.")

    except Exception as exc:
        print(f"\nERROR: {type(exc).__name__}: {exc}")
        raise

    finally:
        if conn is not None:
            conn.close()

        if db is not None:
            db.close()


if __name__ == "__main__":
    main()