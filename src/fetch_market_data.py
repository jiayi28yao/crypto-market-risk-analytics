"""Fetch historical Binance.US candlesticks and save them as Parquet files."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()

BASE_URL = "https://api.binance.us/api/v3/klines"
SYMBOLS = [s.strip().upper() for s in os.getenv("SYMBOLS", "BTCUSDT,BNBUSDT").split(",")]
INTERVAL = os.getenv("INTERVAL", "30m")
START_DATE = os.getenv("START_DATE", "2022-11-01")
END_DATE = os.getenv("END_DATE", "2025-11-01")
LIMIT = 1000

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed"

COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "num_trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]

NUMERIC_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_asset_volume",
    "num_trades",
    "taker_buy_base",
    "taker_buy_quote",
]


def to_milliseconds(value: str) -> int:
    return int(pd.Timestamp(value, tz="UTC").timestamp() * 1000)


def fetch_klines(symbol: str) -> pd.DataFrame:
    """Fetch one symbol using the API's paginated 1,000-row response limit."""
    start_ts = to_milliseconds(START_DATE)
    end_ts = to_milliseconds(END_DATE)
    rows: list[list[object]] = []

    with requests.Session() as session:
        while start_ts < end_ts:
            response = session.get(
                BASE_URL,
                params={
                    "symbol": symbol,
                    "interval": INTERVAL,
                    "startTime": start_ts,
                    "endTime": end_ts - 1,
                    "limit": LIMIT,
                },
                timeout=30,
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break

            rows.extend(batch)
            next_start = int(batch[-1][0]) + 1
            if next_start <= start_ts:
                raise RuntimeError("API pagination did not advance")
            start_ts = next_start
            time.sleep(0.25)

    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True).dt.tz_localize(None)
    frame["close_time"] = pd.to_datetime(frame["close_time"], unit="ms", utc=True).dt.tz_localize(None)
    frame[NUMERIC_COLUMNS] = frame[NUMERIC_COLUMNS].apply(pd.to_numeric)
    frame["symbol"] = symbol.lower()
    return frame.drop_duplicates(subset=["symbol", "open_time"]).sort_values("open_time")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for symbol in SYMBOLS:
        frame = fetch_klines(symbol)
        output_path = DATA_DIR / f"{symbol.lower()}_{INTERVAL}.parquet"
        frame.to_parquet(output_path, engine="pyarrow", index=False)
        print(f"Saved {len(frame):,} rows to {output_path}")


if __name__ == "__main__":
    main()

