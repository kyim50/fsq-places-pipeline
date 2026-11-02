from .config import COLUMNS, SQL_DIR


def apply_schema(conn):
    conn.execute((SQL_DIR / "01_schema.sql").read_text())


def load_raw(cur, csv_path):
    """Empty raw.places, then copy the CSV into it. Returns the row count."""
    cur.execute("TRUNCATE raw.places")
    columns = ", ".join(COLUMNS)
    with open(csv_path, newline="", encoding="utf-8") as f:
        with cur.copy(
            f"COPY raw.places ({columns}) FROM STDIN WITH (FORMAT csv, HEADER match)"
        ) as copy:
            while chunk := f.read(1 << 20):
                copy.write(chunk)
    cur.execute("SELECT count(*) FROM raw.places")
    return cur.fetchone()[0]
def transform(cur, raw_rows):
    """Upsert raw.places into clean.places. Returns row counts for the log."""
    cur.execute("SELECT count(*) FROM clean.places")
    before = cur.fetchone()[0]

    cur.execute((SQL_DIR / "02_transform.sql").read_text())
    changed = cur.rowcount  # rows inserted or updated; unchanged rows are skipped

    cur.execute("SELECT count(*) FROM clean.places")
    total = cur.fetchone()[0]

    # Raw rows with no match in clean were filtered out by the island box.
    cur.execute(
        """SELECT count(*)
           FROM raw.places r
           LEFT JOIN clean.places c USING (fsq_place_id)
           WHERE c.fsq_place_id IS NULL"""
    )
    dropped = cur.fetchone()[0]

    inserted = total - before
    return {
        "dropped": dropped,
        "inserted": inserted,
        "updated": changed - inserted,
        "unchanged": raw_rows - dropped - changed,
        "total": total,
    }
