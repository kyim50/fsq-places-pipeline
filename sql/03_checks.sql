-- Each row is one check. bad_rows = how many rows break it. All zeros means pass.
SELECT 'missing_place_id' AS check_name, count(*) AS bad_rows
FROM raw.places
WHERE fsq_place_id IS NULL OR btrim(fsq_place_id) = ''

UNION ALL
SELECT 'duplicate_place_id', coalesce(sum(n - 1), 0)::bigint
FROM (SELECT count(*) AS n
      FROM raw.places
      WHERE fsq_place_id IS NOT NULL
      GROUP BY btrim(fsq_place_id)
      HAVING count(*) > 1) d

UNION ALL
SELECT 'wrong_country', count(*)
FROM raw.places
WHERE upper(btrim(country)) IS DISTINCT FROM 'JM'

UNION ALL
SELECT 'numeric_coordinates', count(*)
FROM raw.places
WHERE (NULLIF(btrim(latitude), '')  IS NOT NULL AND btrim(latitude)  !~ '^-?[0-9]+(\.[0-9]+)?$')
   OR (NULLIF(btrim(longitude), '') IS NOT NULL AND btrim(longitude) !~ '^-?[0-9]+(\.[0-9]+)?$')

UNION ALL
SELECT 'coordinates_in_range', count(*)
FROM (SELECT CASE WHEN btrim(latitude)  ~ '^-?[0-9]+(\.[0-9]+)?$' THEN btrim(latitude)::double precision  END AS lat,
             CASE WHEN btrim(longitude) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN btrim(longitude)::double precision END AS lon
      FROM raw.places) c
WHERE lat NOT BETWEEN 16.0 AND 20.0
   OR lon NOT BETWEEN -80.0 AND -75.0

UNION ALL
SELECT 'date_format', count(*)
FROM raw.places
WHERE (NULLIF(btrim(date_created), '')   IS NOT NULL AND btrim(date_created)   !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
   OR (NULLIF(btrim(date_refreshed), '') IS NOT NULL AND btrim(date_refreshed) !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
   OR (NULLIF(btrim(date_closed), '')    IS NOT NULL AND btrim(date_closed)    !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$');
