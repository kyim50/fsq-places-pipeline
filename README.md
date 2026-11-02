# Foursquare Jamaica places pipeline

This pipeline loads Foursquare's open places data for Jamaica into PostgreSQL and keeps a clean table for analysts. It downloads a CSV, loads it unchanged into a raw table, runs six data-quality checks, and upserts the result into a clean table. A failed check stops the load. I built it solo for the Harbour City Council open-data brief.

## Run it

You need Docker with Compose. From a fresh clone:

    docker compose up --build --abort-on-container-exit --exit-code-from pipeline

Compose starts PostgreSQL, waits until it is healthy, then runs the pipeline in a second container. The first run builds the image and pulls PostgreSQL, so it takes longer than later runs. A good run ends with `pipeline-1 exited with code 0`. Run the command again and the log reports `0 inserted, 0 updated, 25133 unchanged`.

| Task                               | Command                                                                                                |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Run the pipeline again             | `docker compose run --rm pipeline`                                                                     |
| Trigger a failed check             | `docker compose run --rm pipeline python -m pipeline.run --inject-bad-data`                            |
| Run the analysis query             | `docker compose up -d db`, then `docker compose exec -T db psql -U pipeline places < sql/04_query.sql` |
| Delete the database and start over | `docker compose down -v`                                                                               |

From your own machine, PostgreSQL listens on `localhost:5433`. The user, password and database are `pipeline`, `pipeline` and `places`.

The pipeline exits with 0 on success, 2 when a quality check fails, and 1 on any other error. Each run writes a log to `logs/` and prints the same lines to the console.

## The dataset

The source is Foursquare Open Source Places, release 2026-10-15, licensed under Apache 2.0.

The full release is gated on Hugging Face, needs an access token, is stored as Parquet, and holds about 110 million places worldwide. Someone cloning this repo has none of that. I extracted the Jamaican rows once with DuckDB (`scripts/build_extract.py`) and committed the result as `dataset/fsq_jm_places.csv` (4.5 MB). The pipeline downloads that file over HTTPS from this repo, logs its SHA-256 checksum, and checks that the header has the expected 15 columns before it loads anything.

The source has 25,849 Jamaican places and the CSV has 25,176. The 673 missing places are the ones I excluded as private homes: places labelled `Apartment or Condo` (399) or `Housing Development` (275), with one place carrying both labels. Places with no category at all are kept, so some private homes may remain. One kept row is simply named "Home".

The CSV has 15 of the source's 28 columns. I dropped four contact columns (phone, email, Facebook ID, Twitter) because the file is public and the analysis does not use them. I dropped the geometry, bounding box, category ID and flag columns because a CSV cannot hold them, and latitude and longitude already give each place's location. The category labels are joined into one string with `|` as the separator.

## How it works

1. Extract. Download the CSV to `data/`, log its size and checksum, check the header, and count the rows.
2. Open a transaction. Truncate `raw.places` and copy the CSV into it as text.
3. Run `sql/03_checks.sql` against the raw table. If any check finds bad rows, the load stops.
4. Upsert into `clean.places` with `sql/02_transform.sql`. This converts the types and drops places outside the island box.
5. Commit and log the row counts. If any step fails, the transaction rolls back.

The log shows a row count at each step: rows in the CSV, rows in the raw table, the result of each check, and the rows dropped, inserted, updated and unchanged in the clean table.

## Quality checks

All six run against `raw.places` before anything reaches the clean table.

| Check                  | Stops the load when                                                  |
| ---------------------- | -------------------------------------------------------------------- |
| `missing_place_id`     | a row has no ID                                                      |
| `duplicate_place_id`   | an ID appears more than once (reports the surplus rows)              |
| `wrong_country`        | `country` is not `JM`                                                |
| `numeric_coordinates`  | a latitude or longitude is present but is not a plain decimal number |
| `coordinates_in_range` | a place is outside latitude 16 to 20 or longitude -80 to -75         |
| `date_format`          | a date is present but is not `YYYY-MM-DD`                            |

The checks ask whether the file is broken. The island-box filter in the transform asks whether a record is useful. The source has 43 places outside a tight box around Jamaica (latitude 17.6 to 18.6, longitude -78.5 to -76.1), such as cruise ship venues at sea and places labelled Tampa or Miami Beach. A check on that box would fail on every run, so the check uses the wide range and the tight box is a filter that drops those places and logs how many.

## Design decisions

### Two layers

The raw table holds the file exactly as it arrived, and the clean table has real types and one row per place. Keeping both means I can always see what came in and what the transform dropped. The 43 places outside the island box are still in `raw.places`.

### Raw is text with no key

Every raw column is `text` and the table has no primary key. If a latitude column were numeric, one bad value would abort the whole load before any check could count it. A primary key would reject duplicates before `duplicate_place_id` could report them. Loading as text lets the checks see every problem and say how many rows have it.

### Checks run on raw

The clean table's types and primary key already reject or hide bad values: a latitude of `abc` fails the cast, and a duplicate ID fails the key. On the raw table the checks see everything that arrived.

### One transaction

The truncate, the load, the checks and the upsert share one transaction, so they all succeed or all fail. When a check fails, the rollback leaves raw with the last good file and leaves clean untouched. `evidence/failed-check.log` shows this: the injected run loads 25,181 rows into raw, two checks fail, and raw is back to 25,176 rows afterwards.

### Upsert with DO UPDATE

`clean.places` has `fsq_place_id` as its primary key, and the load uses `INSERT ... ON CONFLICT (fsq_place_id) DO UPDATE`. A rerun can't create duplicates, and corrections in a later release reach the clean table. `DO NOTHING` would also prevent duplicates but would keep stale values.

The update has a `WHERE ... IS DISTINCT FROM` guard that skips rows with no changes. That is why a second run reports 0 updated, and it avoids rewriting 25,000 identical rows. I used `IS DISTINCT FROM` and not `<>` because `<>` returns NULL when either side is NULL. A row that changed from NULL to a value would be skipped.

### The pipeline never deletes

Deleting places that are missing from a newer file needs a rule for telling a closed place from an incomplete file. I left deletes out. A place that disappears from a later release keeps its last known data in `clean.places`.

## The question

Which localities have the most open restaurants, and how many of them list a website?

The query is in `sql/04_query.sql`. A place counts as an open restaurant if it has no `date_closed` and at least one category label starting with `Dining and Drinking > Restaurant`. The query uses `EXISTS`, so a place with two restaurant labels counts once.

| locality             | open_restaurants | with_website | pct_with_website |
| -------------------- | ---------------- | ------------ | ---------------- |
| (no locality listed) | 889              | 8            | 0.9              |
| Kingston             | 477              | 74           | 15.5             |
| Montego Bay          | 231              | 35           | 15.2             |
| Negril               | 117              | 14           | 12.0             |
| Ocho Rios            | 99               | 13           | 13.1             |
| Portmore             | 60               | 8            | 13.3             |
| Mandeville           | 37               | 6            | 16.2             |
| Runaway Bay          | 31               | 2            | 6.5              |
| Falmouth             | 30               | 3            | 10.0             |
| Hanover              | 26               | 1            | 3.8              |

There are 2,483 open restaurants. 889 of them (36%) have no locality, so the locality rankings cover about 64% of restaurants. Website coverage is low everywhere. Among the nine named localities in the top ten it runs from 3.8% in Hanover to 16.2% in Mandeville. The restaurants with no locality are almost all missing a website too: 8 of 889, or 0.9%. Records missing one field tend to miss the other.

Kingston's total is too low. The source also lists `Kingston 10` as a separate locality, and the query counts the two separately.

## Evidence

- `evidence/good-run.log`: the first run, with 25,133 rows inserted.
- `evidence/rerun-no-duplicates.log`: the second run, with 0 inserted and 25,133 unchanged.
- `evidence/failed-check.log`: a run with injected bad data. `duplicate_place_id` finds 5 rows and `coordinates_in_range` finds 1 row, and the load stops.

## Limitations

- Locality is empty for about 37% of places (9,355 of 25,176), so any locality breakdown is partial.
- Places with no category may include private homes. The exclusion only works on places that have a label.
- The source splits Kingston across several numbered localities, and the query does not merge them.
- The island-box filter excludes Jamaica's outlying cays (Pedro and Morant), so a few real places may be dropped.
- "Open" means no `date_closed` value. A place that closed without anyone recording it still counts as open.
- The checks test the file's structure. They cannot tell whether a place is real.
- The CSV is a snapshot of release 2026-10-15. Pulling a newer release means rebuilding the extract, which needs Hugging Face access. The pipeline has no scheduler, and rerunning it is safe because it is idempotent.
- The pipeline never deletes places that disappear from a later release.

## Nine-step notes on PostgreSQL

### 1. What it is

PostgreSQL is an open-source relational database. This project runs version 16 (`postgres:16-alpine`, which reported 16.15 at startup). One database called `places` holds both layers of the pipeline, in two schemas: `raw.places` and `clean.places`.

### 2. Why I used it here

The brief needed three things that PostgreSQL does in one place. A primary key with `ON CONFLICT` keeps a rerun from creating duplicates. A transaction means a failed quality check leaves no half-loaded data. And the category labels are stored as an array, so one SQL query can answer the restaurant question.

### 3. Setup

The `db` service in `docker-compose.yml` does the setup. The image is pinned to major version 16. The user, password and database name come from environment variables with defaults, so the project starts without a `.env` file. A named volume, `pgdata`, is mounted at `/var/lib/postgresql/data` so the data survives between runs. Host port 5433 maps to container port 5432, because 5432 is often taken by a PostgreSQL already installed on the machine. A healthcheck runs `pg_isready` every 3 seconds, and the pipeline container waits for it before starting.

The image creates the user and database only when the data directory is empty. When I first misspelled the variable names, changing the file did nothing until I ran `docker compose down -v` to delete the volume.

### 4. Core concepts

A schema is a folder of tables inside one database. This project uses `raw` and `clean`. A table has typed columns: the raw table is all `text`, and the clean table uses `double precision` for coordinates, `date` for dates, `char(2)` for the country and `text[]` for categories. A primary key is a unique, non-null column with an index behind it, and `clean.places` uses `fsq_place_id`. `NOT NULL` records a rule the data already follows. The profile of the source found no missing names or coordinates.

### 5. Basic usage

`COPY ... FROM STDIN` loads the CSV. The pipeline streams the file through the connection with psycopg, and `\copy` does the same thing inside `psql`. `INSERT ... SELECT` moves rows from raw to clean and converts their types. The analysis query uses `EXISTS`, `unnest`, `GROUP BY` and `count(column)`, which counts only the non-null values. To run it by hand:

    psql -h localhost -p 5433 -U pipeline places -f sql/04_query.sql

### 6. Configuration

The pipeline reads one setting, `DATABASE_URL`. From my own machine it defaults to `localhost:5433`. Inside Compose it is `db:5432`, using the service name and the container's own port. That is the same database seen from two places. Compose fills the credentials from `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB`, each with a default.

### 7. Limits

- If the rows proposed for an upsert contain the same ID twice, PostgreSQL stops with `ON CONFLICT DO UPDATE command cannot affect row a second time`. The duplicate check runs on the raw table first, so the upsert never sees duplicates.
- `COPY ... HEADER match`, which checks the CSV header against the column list, needs PostgreSQL 15 or later. The project uses 16.
- `TRUNCATE` takes an exclusive lock on `raw.places` until the transaction ends, so anything reading the raw table during a run waits. Analysts read `clean.places`, which a run does not lock.
- The default password is `pipeline`. That is acceptable for a local container and wrong for anything reachable from a network.
- The setup is one container on one volume, with no backups and no replication.

### 8. Logs

The pipeline writes its own log to `logs/` for each run, with a row count at every step. Three of those are saved in `evidence/`: a good run, a rerun, and a run that failed a check. PostgreSQL has its own log, and `docker compose logs db` shows it. It records server startup and any SQL error, such as a duplicate key or a `COPY` header mismatch. A failed quality check does not appear there, because the pipeline decides to stop and the rollback is an ordinary event.

### 9. Internals

A transaction can undo more than inserts. `TRUNCATE` rolls back too, which is why the failed-check run goes from 25,181 rows loaded back to the original 25,176 in `raw.places`.

PostgreSQL never edits a row in place. An `UPDATE` writes a new version of the row and leaves the old one to be cleaned up later. Without the `IS DISTINCT FROM` guard, every rerun would write about 25,000 new row versions with identical content.

A primary key is enforced by a unique index. That index is how PostgreSQL refuses a duplicate ID immediately, which is the error I hit when I loaded the same file into the clean table twice.
