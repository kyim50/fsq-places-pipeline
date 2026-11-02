import csv
import hashlib
import logging
import shutil
import time

import requests

from .config import COLUMNS

log = logging.getLogger("pipeline.extract")


def fetch_dataset(url, dest, expected_sha256=""):
    """Download url to dest. A local file path is copied instead."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")

    if url.startswith(("http://", "https://")):
        for attempt in range(1, 4):
            try:
                log.info("downloading %s (attempt %d of 3)", url, attempt)
                with requests.get(url, stream=True, timeout=60) as response:
                    response.raise_for_status()
                    with open(tmp, "wb") as f:
                        for chunk in response.iter_content(chunk_size=1 << 20):
                            f.write(chunk)
                break
            except requests.RequestException as exc:
                log.warning("download failed: %s", exc)
                if attempt == 3:
                    raise
                time.sleep(2 * attempt)
    else:
        log.info("copying local file %s", url)
        shutil.copyfile(url, tmp)

    tmp.replace(dest)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    log.info("saved %s: %d bytes, sha256 %s", dest.name, dest.stat().st_size, digest)
    if expected_sha256 and digest != expected_sha256:
        raise RuntimeError(f"sha256 mismatch: expected {expected_sha256}, got {digest}")
    return dest


def count_rows(path):
    """Check the CSV header matches COLUMNS. Return the number of data rows."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header != COLUMNS:
            raise RuntimeError(f"unexpected CSV header: {header}")
        return sum(1 for _ in reader)
