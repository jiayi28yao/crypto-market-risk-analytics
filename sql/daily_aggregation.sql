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
SELECT
  fo.symbol_id,
  dd.date_id,
  SUBSTRING_INDEX(GROUP_CONCAT(fo.open ORDER BY fo.datetime_id), ',', 1),
  MAX(fo.high),
  MIN(fo.low),
  SUBSTRING_INDEX(GROUP_CONCAT(fo.close ORDER BY fo.datetime_id), ',', -1),
  SUM(fo.volume),
  SUM(fo.quote_asset_volume),
  CASE
    WHEN dd.month IN (12, 1, 2) THEN 1
    WHEN dd.month IN (3, 4, 5) THEN 2
    WHEN dd.month IN (6, 7, 8) THEN 3
    WHEN dd.month IN (9, 10, 11) THEN 4
  END
FROM fact_ohlcv AS fo
JOIN dim_datetime AS dt
  ON fo.datetime_id = dt.datetime_id
JOIN dim_date AS dd
  ON dt.date_id = dd.date_id
WHERE fo.`interval` = '30m'
GROUP BY fo.symbol_id, dd.date_id
ON DUPLICATE KEY UPDATE
  open = VALUES(open),
  high = VALUES(high),
  low = VALUES(low),
  close = VALUES(close),
  volume = VALUES(volume),
  quote_asset_volume = VALUES(quote_asset_volume),
  season_id = VALUES(season_id);

