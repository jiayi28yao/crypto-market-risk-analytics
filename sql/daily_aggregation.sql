USE crypto_db;

INSERT INTO fact_ohlcv_daily (
  symbol_id,
  date_id,
  open,
  high,
  low,
  close,
  volume,
  quote_asset_volume,
  season_id
)
WITH ranked AS (
  SELECT
    fo.symbol_id,
    dt.date_id,
    fo.open,
    fo.high,
    fo.low,
    fo.close,
    fo.volume,
    fo.quote_asset_volume,
    ROW_NUMBER() OVER (
      PARTITION BY fo.symbol_id, dt.date_id
      ORDER BY fo.datetime_id
    ) AS row_first,
    ROW_NUMBER() OVER (
      PARTITION BY fo.symbol_id, dt.date_id
      ORDER BY fo.datetime_id DESC
    ) AS row_last
  FROM fact_ohlcv AS fo
  JOIN dim_datetime AS dt
    ON fo.datetime_id = dt.datetime_id
  WHERE fo.`interval` = '30m'
)
SELECT
  ranked.symbol_id,
  dd.date_id,
  MAX(CASE WHEN ranked.row_first = 1 THEN ranked.open END),
  MAX(ranked.high),
  MIN(ranked.low),
  MAX(CASE WHEN ranked.row_last = 1 THEN ranked.close END),
  SUM(ranked.volume),
  SUM(ranked.quote_asset_volume),
  CASE
    WHEN dd.month IN (12, 1, 2) THEN 1
    WHEN dd.month IN (3, 4, 5) THEN 2
    WHEN dd.month IN (6, 7, 8) THEN 3
    WHEN dd.month IN (9, 10, 11) THEN 4
  END
FROM ranked
JOIN dim_date AS dd
  ON ranked.date_id = dd.date_id
GROUP BY ranked.symbol_id, dd.date_id
ON DUPLICATE KEY UPDATE
  open = VALUES(open),
  high = VALUES(high),
  low = VALUES(low),
  close = VALUES(close),
  volume = VALUES(volume),
  quote_asset_volume = VALUES(quote_asset_volume),
  season_id = VALUES(season_id);
