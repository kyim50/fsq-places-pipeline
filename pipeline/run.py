import argparse
import logging
import sys
import time
from datetime import datetime

import psycopg

from .checks import DataQualityError, run_checks
from .config import DATABASE_URL, DATASET_SHA256, DATASET_URL, DOWNLOAD_PATH, LOG_DIR
from .extract import count_rows, fetch_dataset, inject_bad_data
from .load import apply_schema, load_raw, transform

log = logging.getLogger("pipeline")


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in (
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / f"run-{stamp}.log"),
    ):
        handler.setFormatter(formatter)
        root.addHandler(handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Foursquare Jamaica places pipeline")
    parser.add_argument(
        "--inject-bad-data",
        action="store_true",
        help="add duplicate keys and a 0,0 coordinate so the quality checks fail",
    )
    args = parser.parse_args(argv)

    setup_logging()
    started = time.time()
    log.info("pipeline start")
    try:
        csv_path = fetch_dataset(DATASET_URL, DOWNLOAD_PATH, DATASET_SHA256)
        log.info("extract: %d rows in the CSV", count_rows(csv_path))
        if args.inject_bad_data:
            csv_path = inject_bad_data(csv_path)
            log.warning(
                "injected bad data: %d rows now in %s", count_rows(csv_path), csv_path.name
            )

        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            apply_schema(conn)

            # Load, checks and upsert share one transaction. If a check fails,
            # the rollback leaves raw.places and clean.places as they were.
            with conn.transaction():
                with conn.cursor() as cur:
                    raw_rows = load_raw(cur, csv_path)
                    log.info("raw load: %d rows in raw.places", raw_rows)

                    log.info("quality checks")
                    run_checks(cur)

                    stats = transform(cur, raw_rows)

        log.info(
            "clean load: %d dropped (outside island box), %d inserted, %d updated, %d unchanged",
            stats["dropped"], stats["inserted"], stats["updated"], stats["unchanged"],
        )
        log.info("clean.places now holds %d rows", stats["total"])
        log.info("pipeline finished OK in %.1fs", time.time() - started)
        return 0

    except DataQualityError as exc:
        for name, rows in exc.failures:
            log.error("QUALITY CHECK FAILED: %s (%d rows)", name, rows)
        log.error("load stopped, transaction rolled back, tables unchanged")
        return 2
    except Exception:
        log.exception("pipeline crashed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
