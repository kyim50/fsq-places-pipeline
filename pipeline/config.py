import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"

LOG_DIR = ROOT / "logs"

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://pipeline:pipeline@localhost:5433/places"
)
CSV_PATH =DATASET_URL = os.environ.get(
    "DATASET_URL",
    "https://raw.githubusercontent.com/kyim50/fsq-places-pipeline/main/dataset/fsq_jm_places.csv",
)
DATASET_SHA256 = os.environ.get("DATASET_SHA256", "").strip().lower()
DOWNLOAD_PATH = ROOT / "data" / "fsq_jm_places.csv"

# Same order as the CSV header and as raw.places in sql/01_schema.sql.
COLUMNS = [
    "fsq_place_id", "name", "latitude", "longitude", "address", "locality",
    "region", "postcode", "country", "date_created", "date_refreshed",
    "date_closed", "website", "instagram", "fsq_category_labels",
]
