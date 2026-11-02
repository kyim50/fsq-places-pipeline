import sys
from turtle import title
import duckdb

src = sys.argv[1]
con= duckdb.connect()

def show(title, sql):
    print(f"\n=== {title} ===")
    con.sql(sql).show(max_rows=50)

show("columns and types", f"DESCRIBE SELECT * FROM '{src}'")

show("size, keys, nulls, ranges", f"""
    SELECT count(*)                                  AS total_rows,
           count(DISTINCT fsq_place_id)              AS distinct_ids,
           count(*) - count(name)                    AS null_name,
           count(*) - count(latitude)                AS null_lat,
           count(*) - count(longitude)               AS null_lon,
           count(*) FILTER (WHERE date_closed IS NOT NULL) AS closed,
           min(latitude)  AS min_lat,  max(latitude)  AS max_lat,
           min(longitude) AS min_lon,  max(longitude) AS max_lon
    FROM '{src}'
""")

show("countries", f"""
    SELECT country, count(*) AS n FROM '{src}' GROUP BY country
""")

show("sample rows", f"""
    SELECT fsq_place_id, name, locality, latitude, longitude,
           date_created, date_closed, website
    FROM '{src}' LIMIT 5
""")

show("category labels", f"""
    SELECT fsq_category_labels FROM '{src}'
    WHERE fsq_category_labels IS NOT NULL LIMIT 5
""")

show("top localities", f"""
    SELECT locality, count(*) AS n FROM '{src}'
    GROUP BY locality ORDER BY n DESC LIMIT 10
""")

show("rows outside the island box", f"""
    SELECT count(*) AS outside_box
    FROM '{src}'
    WHERE latitude  NOT BETWEEN 17.6 AND 18.6
       OR longitude NOT BETWEEN -78.5 AND -76.1
""")

show("examples outside the box", f"""
    SELECT name, locality, latitude, longitude
    FROM '{src}'
    WHERE latitude  NOT BETWEEN 17.6 AND 18.6
       OR longitude NOT BETWEEN -78.5 AND -76.1
    LIMIT 15
""")
