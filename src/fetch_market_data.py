"""Fetch historical Binance.US candlesticks and save them as Parquet files."""

from __future__ import annotations

import os
import time
from datetime import timedelta
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


def validate_frame(frame: pd.DataFrame, symbol: str) -> list[str]:
    """Validate one downloaded series and return non-fatal continuity warnings."""
    if frame.empty:
        raise ValueError(f"No rows returned for {symbol}")
    if frame["open_time"].duplicated().any():
        raise ValueError(f"Duplicate candle timestamps found for {symbol}")
    if frame[COLUMNS[:-1]].isna().any().any():
        raise ValueError(f"Missing required values found for {symbol}")

    invalid_ohlc = (
        (frame["high"] < frame[["open", "close", "low"]].max(axis=1))
        | (frame["low"] > frame[["open", "close", "high"]].min(axis=1))
    )
    if invalid_ohlc.any():
        raise ValueError(f"Invalid OHLC relationships found for {symbol}")
    if (frame[NUMERIC_COLUMNS] < 0).any().any():
        raise ValueError(f"Negative market values found for {symbol}")

    warnings: list[str] = []
    interval_units = {
        "m": lambda value: timedelta(minutes=value),
        "h": lambda value: timedelta(hours=value),
        "d": lambda value: timedelta(days=value),
        "w": lambda value: timedelta(weeks=value),
    }
    suffix = INTERVAL[-1]
    if suffix not in interval_units or not INTERVAL[:-1].isdigit():
        raise ValueError(f"Unsupported interval for continuity checks: {INTERVAL}")
    expected_step = interval_units[suffix](int(INTERVAL[:-1]))
    gaps = frame["open_time"].sort_values().diff()
    for index in gaps[gaps > expected_step].index:
        end = frame.loc[index, "open_time"]
        start = end - gaps.loc[index]
        missing = int(gaps.loc[index] / expected_step) - 1
        warnings.append(
            f"{symbol}: {missing} missing candles between {start} and {end}"
        )
    return warnings


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
    frame = frame.sort_values("open_time").reset_index(drop=True)
    for warning in validate_frame(frame, symbol):
        print(f"WARNING: {warning}")
    return frame


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for symbol in SYMBOLS:
        frame = fetch_klines(symbol)
        output_path = DATA_DIR / f"{symbol.lower()}_{INTERVAL}.parquet"
        frame.to_parquet(output_path, engine="pyarrow", index=False)
        print(f"Saved {len(frame):,} rows to {output_path}")


if __name__ == "__main__":
    main()
