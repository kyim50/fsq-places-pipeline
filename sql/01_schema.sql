CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.places (
    fsq_place_id        text,
    name                text,
    latitude            text,
    longitude           text,
    address             text,
    locality            text,
    region              text,
    postcode            text,
    country             text,
    date_created        text,
    date_refreshed      text,
    date_closed         text,
    website             text,
    instagram           text,
    fsq_category_labels text,
    _loaded_at          timestamptz NOT NULL DEFAULT now()
);

CREATE SCHEMA IF NOT EXISTS clean;

CREATE TABLE IF NOT EXISTS clean.places (
    fsq_place_id   text PRIMARY KEY,
    name           text             NOT NULL,
    latitude       double precision NOT NULL,
    longitude      double precision NOT NULL,
    address        text,
    locality       text,
    region         text,
    postcode       text,
    country        char(2)          NOT NULL,
    date_created   date,
    date_refreshed date,
    date_closed    date,
    website        text,
    instagram      text,
    categories     text[],
    loaded_at      timestamptz      NOT NULL DEFAULT now()
);
