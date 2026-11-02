import logging

from .config import SQL_DIR

log = logging.getLogger("pipeline.checks")


class DataQualityError(Exception):
    def __init__(self, failures):
        self.failures = failures  # list of (check_name, bad_rows)
        super().__init__(", ".join(f"{name}: {rows} rows" for name, rows in failures))


def run_checks(cur):
    """Run sql/03_checks.sql. Raise DataQualityError if any check has bad rows."""
    cur.execute((SQL_DIR / "03_checks.sql").read_text())
    results = sorted(cur.fetchall())
    failures = []
    for name, bad_rows in results:
        if bad_rows:
            log.error("check FAILED  %-22s %d rows", name, bad_rows)
            failures.append((name, bad_rows))
        else:
            log.info("check passed  %-22s 0 rows", name)
    if failures:
        raise DataQualityError(failures)
