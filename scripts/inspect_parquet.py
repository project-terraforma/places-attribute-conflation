"""
Explore places attribute conflation dataset using DuckDB.
Run from project root: python scripts/project_data.py
"""
import duckdb
from pathlib import Path

# Use path relative to script location so it works from any cwd
DATA_PATH = Path(__file__).parent.parent / "data" / "project_a_samples.parquet"

con = duckdb.connect()

print("=" * 60)
print("PLACES ATTRIBUTE CONFLATION — Dataset Overview")
print("=" * 60)

# --- Schema ---
print("\nSCHEMA (columns & types)")
print("-" * 40)
schema = con.execute(f"DESCRIBE SELECT * FROM '{DATA_PATH}'").fetchdf()
for _, row in schema.iterrows():
    print(f"  {row['column_name']:<20} {row['column_type']}")

# --- Row count ---
row_count = con.execute(f"SELECT COUNT(*) FROM '{DATA_PATH}'").fetchone()[0]
print(f"\nROW COUNT: {row_count:,}")

# --- Null/missing stats ---
print("\nNULL COUNTS per column")
print("-" * 40)
null_counts = []
for col in schema["column_name"]:
    n = con.execute(f"SELECT COUNT(*) FROM '{DATA_PATH}' WHERE {col} IS NULL").fetchone()[0]
    pct = 100 * n / row_count
    null_counts.append((col, n, pct))
for col, n, pct in sorted(null_counts, key=lambda x: -x[1]):
    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
    print(f"  {col:<20} {n:>5} ({pct:5.1f}%) {bar}")

# --- Confidence distribution ---
print("\nCONFIDENCE distribution (conflated vs base)")
print("-" * 40)
conf_stats = con.execute(f"""
    SELECT
        ROUND(confidence, 2) AS conf_bin,
        COUNT(*) AS cnt
    FROM '{DATA_PATH}'
    WHERE confidence IS NOT NULL
    GROUP BY conf_bin
    ORDER BY conf_bin DESC
    LIMIT 10
""").fetchdf()
print(conf_stats.to_string(index=False))
base_conf = con.execute(f"""
    SELECT
        MIN(base_confidence) AS min_base,
        MAX(base_confidence) AS max_base,
        AVG(base_confidence) AS avg_base
    FROM '{DATA_PATH}'
    WHERE base_confidence IS NOT NULL
""").fetchone()
print(f"\n  base_confidence: min={base_conf[0]:.2f}, max={base_conf[1]:.2f}, avg={base_conf[2]:.2f}")

# --- Sample of key attributes ---
print("\nSAMPLE ROWS (key attributes)")
print("-" * 40)
sample = con.execute(f"""
    SELECT id, base_id, names, categories, confidence,
           base_names, base_categories, base_confidence
    FROM '{DATA_PATH}'
    LIMIT 5
""").fetchdf()
print(sample.to_string())

# --- Uniqueness ---
print("\nUNIQUENESS")
print("-" * 40)
unique_id = con.execute(f"SELECT COUNT(DISTINCT id) FROM '{DATA_PATH}'").fetchone()[0]
unique_base = con.execute(f"SELECT COUNT(DISTINCT base_id) FROM '{DATA_PATH}'").fetchone()[0]
print(f"  Unique id:       {unique_id:,}")
print(f"  Unique base_id:  {unique_base:,}")
if unique_base < row_count:
    dupes = con.execute(f"""
        SELECT base_id, COUNT(*) AS n
        FROM '{DATA_PATH}'
        GROUP BY base_id
        HAVING COUNT(*) > 1
        ORDER BY n DESC
        LIMIT 5
    """).fetchdf()
    print(f"  (Multiple conflated records per base_id; top duplicate bases:)")
    print(dupes.to_string(index=False))

# --- Full sample (all columns) ---
print("\nFULL SAMPLE (first row, all columns)")
print("-" * 40)
full_row = con.execute(f"SELECT * FROM '{DATA_PATH}' LIMIT 1").fetchdf()
for col in full_row.columns:
    val = full_row[col].iloc[0]
    val_str = str(val)[:80] + "..." if val is not None and len(str(val)) > 80 else str(val)
    print(f"  {col}: {val_str}")

print("\n" + "=" * 60)

con.close()