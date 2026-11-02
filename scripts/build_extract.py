import sys
from pathlib import Path

import duckdb

src = sys.argv[1]
out = Path("dataset/fsq_jm_places.csv")
out.parent.mkdir(exist_ok=True)

# Columns the pipeline needs. Everything else in the Parquet file is dropped.
COLUMNS = [
    "fsq_place_id", "name", "latitude", "longitude", "address", "locality",
    "region", "postcode", "country", "date_created", "date_refreshed",
    "date_closed", "website", "instagram",
]

# Fill this in after you have reviewed the labels printed below.

EXCLUDE_LABELS = [
    "Community and Government > Residential Building > Apartment or Condo",
    "Community and Government > Housing Development",
]
con = duckdb.connect()

print("Labels that mention homes or housing (review these):")
con.sql(f"""
    SELECT label, count(*) AS n
    FROM (SELECT unnest(fsq_category_labels) AS label FROM '{src}')
    WHERE lower(label) LIKE '%resid%'
       OR lower(label) LIKE '%home%'
       OR lower(label) LIKE '%housing%'
    GROUP BY label
    ORDER BY n DESC
""").show(max_rows=50)

where = "country = 'JM' AND fsq_category_labels IS NOT NULL"
if EXCLUDE_LABELS:
    quoted = ", ".join("'" + label.replace("'", "''") + "'" for label in EXCLUDE_LABELS)
    where += f" AND NOT coalesce(list_has_any(fsq_category_labels, [{quoted}]), false)"

cols = ", ".join(COLUMNS)
con.execute(f"""
    COPY (
        SELECT {cols},
               array_to_string(fsq_category_labels, ' | ') AS fsq_category_labels
        FROM '{src}'
        WHERE {where}
        ORDER BY fsq_place_id
    ) TO '{out}' (FORMAT csv, HEADER)
""")

total = con.execute(f"SELECT count(*) FROM '{src}'").fetchone()[0]
kept = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
print(f"read {total} rows, wrote {kept} rows to {out}")
