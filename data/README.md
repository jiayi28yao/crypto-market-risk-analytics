# Data files

`processed/` contains the two Parquet datasets used by the notebook and database loader:

- `btcusdt_30m.parquet`
- `bnbusdt_30m.parquet`

Each row is a 30-minute Binance.US candlestick with open, high, low, close, volume, quote volume, trade count, taker-buy volume, timestamps, and symbol. The included files cover November 2022 through October 2025.

Run `python src/fetch_market_data.py` from the repository root to regenerate these files from the public Binance.US candlestick endpoint.

