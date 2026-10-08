CREATE DATABASE IF NOT EXISTS crypto_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE crypto_db;

CREATE TABLE IF NOT EXISTS dim_symbol (
  symbol_id INT AUTO_INCREMENT PRIMARY KEY,
  symbol VARCHAR(20) NOT NULL UNIQUE,
  base_asset VARCHAR(20) NOT NULL,
  quote_asset VARCHAR(20) NOT NULL,
  exchange VARCHAR(30) NOT NULL DEFAULT 'Binance.US',
  launch_date DATE NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
  date_id INT UNSIGNED PRIMARY KEY,
  d DATE NOT NULL UNIQUE,
  year SMALLINT NOT NULL,
  month TINYINT UNSIGNED NOT NULL,
  day TINYINT UNSIGNED NOT NULL,
  weekday TINYINT UNSIGNED NOT NULL,
  week_of_year TINYINT UNSIGNED NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_datetime (
  datetime_id BIGINT UNSIGNED PRIMARY KEY,
  dt DATETIME(6) NOT NULL UNIQUE,
  date_id INT UNSIGNED NOT NULL,
  hour TINYINT UNSIGNED NOT NULL,
  minute TINYINT UNSIGNED NOT NULL,
  second TINYINT UNSIGNED NOT NULL,
  CONSTRAINT fk_datetime_date
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

CREATE TABLE IF NOT EXISTS dim_season (
  season_id TINYINT UNSIGNED PRIMARY KEY,
  season_name VARCHAR(20) NOT NULL UNIQUE
);

INSERT INTO dim_season (season_id, season_name) VALUES
  (1, 'Winter'),
  (2, 'Spring'),
  (3, 'Summer'),
  (4, 'Fall')
ON DUPLICATE KEY UPDATE season_name = VALUES(season_name);

CREATE TABLE IF NOT EXISTS fact_ohlcv (
  ohlcv_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  symbol_id INT NOT NULL,
  datetime_id BIGINT UNSIGNED NOT NULL,
  `interval` VARCHAR(10) NOT NULL,
  open DECIMAL(18,6) NOT NULL,
  high DECIMAL(18,6) NOT NULL,
  low DECIMAL(18,6) NOT NULL,
  close DECIMAL(18,6) NOT NULL,
  volume DECIMAL(24,8) NOT NULL,
  quote_asset_volume DECIMAL(24,8) NOT NULL,
  num_trades INT NOT NULL,
  taker_buy_base DECIMAL(24,8) NOT NULL,
  taker_buy_quote DECIMAL(24,8) NOT NULL,
  vwap DECIMAL(24,8)
    GENERATED ALWAYS AS (quote_asset_volume / NULLIF(volume, 0)) STORED,
  UNIQUE KEY uq_ohlcv_symbol_datetime_interval (symbol_id, datetime_id, `interval`),
  KEY ix_ohlcv_datetime (datetime_id),
  CONSTRAINT fk_ohlcv_symbol
    FOREIGN KEY (symbol_id) REFERENCES dim_symbol(symbol_id),
  CONSTRAINT fk_ohlcv_datetime
    FOREIGN KEY (datetime_id) REFERENCES dim_datetime(datetime_id)
);

CREATE TABLE IF NOT EXISTS fact_ohlcv_daily (
  daily_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  symbol_id INT NOT NULL,
  date_id INT UNSIGNED NOT NULL,
  open DECIMAL(18,6) NOT NULL,
  high DECIMAL(18,6) NOT NULL,
  low DECIMAL(18,6) NOT NULL,
  close DECIMAL(18,6) NOT NULL,
  volume DECIMAL(24,8) NOT NULL,
  quote_asset_volume DECIMAL(24,8) NOT NULL,
  season_id TINYINT UNSIGNED NULL,
  UNIQUE KEY uq_daily_symbol_date (symbol_id, date_id),
  KEY ix_daily_date (date_id),
  KEY ix_daily_season (season_id),
  CONSTRAINT fk_daily_symbol
    FOREIGN KEY (symbol_id) REFERENCES dim_symbol(symbol_id),
  CONSTRAINT fk_daily_date
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
  CONSTRAINT fk_daily_season
    FOREIGN KEY (season_id) REFERENCES dim_season(season_id)
);

