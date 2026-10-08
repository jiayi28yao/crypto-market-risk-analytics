# Data files

`processed/` contains the two Parquet datasets used by the notebook and database loader:

- `btcusdt_30m.parquet`
- `bnbusdt_30m.parquet`

Each row is a 30-minute Binance.US candlestick with open, high, low, close, volume, quote volume, trade count, taker-buy volume, timestamps, and symbol. Each file contains 52,594 rows covering November 1, 2022 through October 31, 2025.

Both assets contain the same source-data continuity gap on February 6, 2023. Fourteen expected 30-minute candles are absent between 04:30 and 12:00 UTC. The gap is retained rather than imputed because fabricated prices or volumes would distort risk estimates.

Run `python src/validate_data.py` to verify row counts, ranges, duplicate keys, required values, numeric parsing, non-negative market fields, OHLC relationships, and timestamp gaps.

Run `python src/fetch_market_data.py` from the repository root to regenerate these files from the public Binance.US candlestick endpoint.
