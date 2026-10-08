
"""
CTC Graph Construction Engine

Initializes the Kuzu graph database, defines the schema,
and ingests node and relationship CSV files.
"""

from pathlib import Path
import shutil
import sys

import kuzu


# ============================================================
# 1. CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DB_PATH = Path(r"E:\ctc-retail-fraud-graph\kuzu_db")

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# Set to True only when you intentionally want a clean rebuild.
REBUILD_DB = True


# ============================================================
# 2. CSV FILE DEFINITIONS
# ============================================================

CSV_FILES = {
    "Person nodes": PROCESSED_DIR / "nodes_person.csv",
    "Token nodes": PROCESSED_DIR / "nodes_token.csv",
    "Transaction nodes": PROCESSED_DIR / "nodes_transaction.csv",
    "Store nodes": RAW_DIR / "stores.csv",
    "Product nodes": RAW_DIR / "products.csv",
    "Person-Transaction edges": PROCESSED_DIR / "edges_person_tx.csv",
    "Transaction-Token edges": PROCESSED_DIR / "edges_tx_token.csv",
    "Transaction-Store edges": PROCESSED_DIR / "edges_tx_store.csv",
    "Transaction-Product edges": PROCESSED_DIR / "edges_tx_product.csv",
}


def validate_files():
    """Check that every required CSV exists before building the graph."""

    print("\nChecking required CSV files...")

    missing_files = [
        (label, path)
        for label, path in CSV_FILES.items()
        if not path.is_file()
    ]

    if missing_files:
        print("\nERROR: The following files are missing:")

        for label, path in missing_files:
            print(f"  - {label}: {path}")

        raise FileNotFoundError(
            f"{len(missing_files)} required CSV file(s) are missing."
        )

    print(f"All {len(CSV_FILES)} required CSV files were found.")


# ============================================================
# 3. DATABASE RESET
# ============================================================

def reset_database():
    """Remove the existing database when a clean rebuild is requested."""

    if not REBUILD_DB:
        print("\nKeeping the existing database.")
        return

    print(f"\nPreparing database path: {DB_PATH}")

    # Create the parent directory, not the database directory itself.
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DB_PATH.is_dir():
        print("Removing existing database directory...")
        shutil.rmtree(DB_PATH)

    elif DB_PATH.is_file():
        raise RuntimeError(
            f"The database path is an existing FILE, not a directory:\n"
            f"{DB_PATH}\n"
            "Inspect this file and choose a valid database path."
        )

    print("Database reset completed.")


# ============================================================
# 4. CSV PATH HELPER
# ============================================================

def copy_csv(conn, table_name, csv_path):
    """Import a CSV using a normalized, safely quoted file path."""

    # Forward slashes work well for Windows paths in Kuzu queries.
    csv_path = csv_path.resolve().as_posix()

    # Escape apostrophes in the SQL string literal.
    csv_path = csv_path.replace("'", "''")

    query = (
        f"COPY {table_name} FROM '{csv_path}' "
        "(HEADER=true)"
    )

    print(f"  -> Importing {table_name}...")
    conn.execute(query)


# ============================================================
# 5. GRAPH SCHEMA
# ============================================================

def build_schema(conn: kuzu.Connection):
    """Create node tables and relationship tables."""

    print("\nDefining graph schema...")

    # -------------------- NODE TABLES --------------------

    conn.execute("""
        CREATE NODE TABLE Person (
            id STRING,
            PRIMARY KEY (id)
        )
    """)

    conn.execute("""
        CREATE NODE TABLE Token (
            id STRING,
            PRIMARY KEY (id)
        )
    """)

    conn.execute("""
        CREATE NODE TABLE Transaction (
            id STRING,
            transaction_type STRING,
            amount DOUBLE,
            timestamp TIMESTAMP,
            is_receipted BOOLEAN,
            PRIMARY KEY (id)
        )
    """)

    conn.execute("""
        CREATE NODE TABLE Store (
            store_id STRING,
            name STRING,
            city STRING,
            region STRING,
            PRIMARY KEY (store_id)
        )
    """)

    conn.execute("""
        CREATE NODE TABLE Product (
            sku STRING,
            name STRING,
            category STRING,
            price DOUBLE,
            theft_tier STRING,
            PRIMARY KEY (sku)
        )
    """)

    # ---------------- RELATIONSHIP TABLES ----------------

    conn.execute("""
        CREATE REL TABLE Person_Tx (
            FROM Person TO Transaction
        )
    """)

    conn.execute("""
        CREATE REL TABLE Tx_Token (
            FROM Transaction TO Token
        )
    """)

    conn.execute("""
        CREATE REL TABLE Tx_Store (
            FROM Transaction TO Store
        )
    """)

    conn.execute("""
        CREATE REL TABLE Tx_Product (
            FROM Transaction TO Product
        )
    """)

    print("Graph schema created successfully.")


# ============================================================
# 6. DATA INGESTION
# ============================================================

def ingest_data(conn: kuzu.Connection):
    """Load all node and relationship CSV files into Kuzu."""

    print("\nIngesting node data...")

    # Nodes
    copy_csv(conn, "Person", PROCESSED_DIR / "nodes_person.csv")
    copy_csv(conn, "Token", PROCESSED_DIR / "nodes_token.csv")
    copy_csv(
        conn,
        "Transaction",
        PROCESSED_DIR / "nodes_transaction.csv",
    )
    copy_csv(conn, "Store", RAW_DIR / "stores.csv")
    copy_csv(conn, "Product", RAW_DIR / "products.csv")

    print("\nIngesting relationship data...")

    # Relationships
    copy_csv(
        conn,
        "Person_Tx",
        PROCESSED_DIR / "edges_person_tx.csv",
    )
    copy_csv(
        conn,
        "Tx_Token",
        PROCESSED_DIR / "edges_tx_token.csv",
    )
    copy_csv(
        conn,
        "Tx_Store",
        PROCESSED_DIR / "edges_tx_store.csv",
    )
    copy_csv(
        conn,
        "Tx_Product",
        PROCESSED_DIR / "edges_tx_product.csv",
    )

    print("\nAll CSV import commands completed.")


# ============================================================
# 7. VERIFICATION
# ============================================================

def verify_graph(conn: kuzu.Connection):
    """Verify that each expected table is queryable."""

    print("\nVerifying graph tables...")

    queries = {
        "Person": "MATCH (n:Person) RETURN count(n) AS total",
        "Token": "MATCH (n:Token) RETURN count(n) AS total",
        "Transaction": (
            "MATCH (n:Transaction) RETURN count(n) AS total"
        ),
        "Store": "MATCH (n:Store) RETURN count(n) AS total",
        "Product": "MATCH (n:Product) RETURN count(n) AS total",
        "Person_Tx": (
            "MATCH (:Person)-[r:Person_Tx]->(:Transaction) "
            "RETURN count(r) AS total"
        ),
        "Tx_Token": (
            "MATCH (:Transaction)-[r:Tx_Token]->(:Token) "
            "RETURN count(r) AS total"
        ),
        "Tx_Store": (
            "MATCH (:Transaction)-[r:Tx_Store]->(:Store) "
            "RETURN count(r) AS total"
        ),
        "Tx_Product": (
            "MATCH (:Transaction)-[r:Tx_Product]->(:Product) "
            "RETURN count(r) AS total"
        ),
    }

    for table_name, query in queries.items():
        result = conn.execute(query)
        result.has_next()
        row = result.get_next()
        print(f"  {table_name}: {row[0]} records")


# ============================================================
# 8. MAIN EXECUTION
# ============================================================

def main():
    print("=" * 65)
    print("CTC FRAUD ENGINE: GRAPH CONSTRUCTION")
    print("=" * 65)

    db = None
    conn = None

    try:
        # Validate inputs BEFORE deleting an existing database.
        validate_files()

        reset_database()

        print("\nInitializing Kuzu database...")
        db = kuzu.Database(str(DB_PATH))
        conn = kuzu.Connection(db)

        build_schema(conn)
        ingest_data(conn)
        verify_graph(conn)

        print("\n" + "=" * 65)
        print("GRAPH DATABASE BUILT AND VERIFIED")
        print(f"Database location: {DB_PATH}")
        print("=" * 65)

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