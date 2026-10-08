
from pathlib import Path
import kuzu

p = Path(r"E:\ctc-retail-fraud-graph\kuzu_db")

print("Kuzu version:", getattr(kuzu, "__version__", "unknown"))
print("Path:", p)
print("File:", p.is_file())
print("Size:", p.stat().st_size if p.exists() else "missing")

# Check whether Kuzu can open this path as a database.
try:
    db = kuzu.Database(str(p))
    conn = kuzu.Connection(db)

    print("Kuzu opened the database successfully.")

    result = conn.execute("MATCH (n) RETURN count(n) AS total")
    print("Total nodes:", result.get_as_df())

    conn.close()
    db.close()

except Exception as exc:
    print("Database open failed:", type(exc).__name__, str(exc))