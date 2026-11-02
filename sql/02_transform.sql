INSERT INTO clean.places
    (fsq_place_id, name, latitude, longitude, address, locality, region, postcode,
     country, date_created, date_refreshed, date_closed, website, instagram, categories)
SELECT fsq_place_id,
       name,
       latitude::double precision,
       longitude::double precision,
       NULLIF(btrim(address), ''),
       NULLIF(btrim(locality), ''),
       NULLIF(btrim(region), ''),
       NULLIF(btrim(postcode), ''),
       country,
       NULLIF(btrim(date_created), '')::date,
       NULLIF(btrim(date_refreshed), '')::date,
       NULLIF(btrim(date_closed), '')::date,
       NULLIF(btrim(website), ''),
       NULLIF(btrim(instagram), ''),
       string_to_array(NULLIF(btrim(fsq_category_labels), ''), ' | ')
FROM raw.places
WHERE latitude::double precision  BETWEEN 17.6 AND 18.6
  AND longitude::double precision BETWEEN -78.5 AND -76.1
ON CONFLICT (fsq_place_id) DO UPDATE SET
    name           = EXCLUDED.name,
    latitude       = EXCLUDED.latitude,
    longitude      = EXCLUDED.longitude,
    address        = EXCLUDED.address,
    locality       = EXCLUDED.locality,
    region         = EXCLUDED.region,
    postcode       = EXCLUDED.postcode,
    country        = EXCLUDED.country,
    date_created   = EXCLUDED.date_created,
    date_refreshed = EXCLUDED.date_refreshed,
    date_closed    = EXCLUDED.date_closed,
    website        = EXCLUDED.website,
    instagram      = EXCLUDED.instagram,
    categories     = EXCLUDED.categories,
    loaded_at      = now()
WHERE (clean.places.name, clean.places.latitude, clean.places.longitude, clean.places.address,
       clean.places.locality, clean.places.region, clean.places.postcode, clean.places.country,
       clean.places.date_created, clean.places.date_refreshed, clean.places.date_closed,
       clean.places.website, clean.places.instagram, clean.places.categories)
      IS DISTINCT FROM
      (EXCLUDED.name, EXCLUDED.latitude, EXCLUDED.longitude, EXCLUDED.address,
       EXCLUDED.locality, EXCLUDED.region, EXCLUDED.postcode, EXCLUDED.country,
       EXCLUDED.date_created, EXCLUDED.date_refreshed, EXCLUDED.date_closed,
       EXCLUDED.website, EXCLUDED.instagram, EXCLUDED.categories);

