-- Question: where are Jamaica's open restaurants, and how many of them list a website?
SELECT coalesce(locality, '(no locality listed)') AS locality,
       count(*)                                    AS open_restaurants,
       count(website)                              AS with_website,
       round(100.0 * count(website) / count(*), 1) AS pct_with_website
FROM clean.places
WHERE date_closed IS NULL
  AND EXISTS (SELECT 1
              FROM unnest(categories) AS label
              WHERE label LIKE 'Dining and Drinking > Restaurant%')
GROUP BY 1
ORDER BY open_restaurants DESC, locality
LIMIT 10;
