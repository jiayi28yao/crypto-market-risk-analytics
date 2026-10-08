"""Load project Parquet files into the MySQL star schema."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed"

REQUIRED_COLUMNS = {
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_asset_volume",
    "num_trades",
    "taker_buy_base",
    "taker_buy_quote",
    "symbol",
}

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


def database_url() -> str:
    user = quote_plus(os.getenv("MYSQL_USER", "root"))
    password = quote_plus(os.environ["MYSQL_PASSWORD"])
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "crypto_db")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


def datetime_id(series: pd.Series) -> pd.Series:
    return series.dt.strftime("%Y%m%d%H%M%S%f").str[:-3].astype("int64")


def insert_in_chunks(connection, statement, records: list[dict], chunk_size: int = 2000) -> None:
    for start in range(0, len(records), chunk_size):
        connection.execute(statement, records[start : start + chunk_size])


def load_file(engine, parquet_path: Path) -> None:
    frame = pd.read_parquet(parquet_path)
    if frame.empty:
        return

    missing_columns = REQUIRED_COLUMNS.difference(frame.columns)
    if missing_columns:
        raise ValueError(
            f"{parquet_path.name} is missing columns: {sorted(missing_columns)}"
        )
    if frame[list(REQUIRED_COLUMNS)].isna().any().any():
        raise ValueError(f"{parquet_path.name} contains missing required values")
    if frame.duplicated(subset=["symbol", "open_time"]).any():
        raise ValueError(f"{parquet_path.name} contains duplicate symbol/timestamp rows")

    frame["open_time"] = pd.to_datetime(frame["open_time"])
    frame[NUMERIC_COLUMNS] = frame[NUMERIC_COLUMNS].apply(pd.to_numeric, errors="raise")
    frame = frame.copy()
    symbols = frame["symbol"].astype(str).str.upper().unique()
    if len(symbols) != 1:
        raise ValueError(f"{parquet_path.name} must contain exactly one symbol")
    if frame[NUMERIC_COLUMNS].isna().any().any():
        raise ValueError(f"{parquet_path.name} contains missing numeric values")
    if (frame[NUMERIC_COLUMNS] < 0).any().any():
        raise ValueError(f"{parquet_path.name} contains negative market values")

    invalid_ohlc = (
        (frame["high"] < frame[["open", "close", "low"]].max(axis=1))
        | (frame["low"] > frame[["open", "close", "high"]].min(axis=1))
    )
    if invalid_ohlc.any():
        raise ValueError(f"{parquet_path.name} contains invalid OHLC relationships")

    symbol = str(frame["symbol"].iloc[0]).upper()
    base_asset, quote_asset = symbol[:-4], symbol[-4:]
    interval = parquet_path.stem.rsplit("_", 1)[-1]

    symbol_upsert = text(
        """
        INSERT INTO dim_symbol (symbol, base_asset, quote_asset)
        VALUES (:symbol, :base_asset, :quote_asset)
        ON DUPLICATE KEY UPDATE
          base_asset = VALUES(base_asset),
          quote_asset = VALUES(quote_asset)
        """
    )

    date_insert = text(
        """
        INSERT IGNORE INTO dim_date
          (date_id, d, year, month, day, weekday, week_of_year)
        VALUES
          (:date_id, :d, :year, :month, :day, :weekday, :week_of_year)
        """
    )

    datetime_insert = text(
        """
        INSERT IGNORE INTO dim_datetime
          (datetime_id, dt, date_id, hour, minute, second)
        VALUES
          (:datetime_id, :dt, :date_id, :hour, :minute, :second)
        """
    )

    fact_upsert = text(
        """
        INSERT INTO fact_ohlcv
          (symbol_id, datetime_id, `interval`, open, high, low, close, volume,
           quote_asset_volume, num_trades, taker_buy_base, taker_buy_quote)
        VALUES
          (:symbol_id, :datetime_id, :interval, :open, :high, :low, :close, :volume,
           :quote_asset_volume, :num_trades, :taker_buy_base, :taker_buy_quote)
        ON DUPLICATE KEY UPDATE
          open = VALUES(open), high = VALUES(high), low = VALUES(low),
          close = VALUES(close), volume = VALUES(volume),
          quote_asset_volume = VALUES(quote_asset_volume),
          num_trades = VALUES(num_trades),
          taker_buy_base = VALUES(taker_buy_base),
          taker_buy_quote = VALUES(taker_buy_quote)
        """
    )

    unique_dates = frame["open_time"].dt.normalize().drop_duplicates().sort_values()
    iso_calendar = unique_dates.dt.isocalendar()
    date_records = [
        {
            "date_id": int(value.strftime("%Y%m%d")),
            "d": value.date(),
            "year": value.year,
            "month": value.month,
            "day": value.day,
            "weekday": value.weekday(),
            "week_of_year": int(week),
        }
        for value, week in zip(unique_dates, iso_calendar.week)
    ]

    frame["datetime_id"] = datetime_id(frame["open_time"])
    frame["date_id"] = frame["open_time"].dt.strftime("%Y%m%d").astype("int64")
    datetime_records = [
        {
            "datetime_id": int(row.datetime_id),
            "dt": row.open_time.to_pydatetime(),
            "date_id": int(row.date_id),
            "hour": row.open_time.hour,
            "minute": row.open_time.minute,
            "second": row.open_time.second,
        }
        for row in frame[["datetime_id", "open_time", "date_id"]].itertuples(index=False)
    ]

    with engine.begin() as connection:
        connection.execute(
            symbol_upsert,
            {"symbol": symbol, "base_asset": base_asset, "quote_asset": quote_asset},
        )
        symbol_id = connection.execute(
            text("SELECT symbol_id FROM dim_symbol WHERE symbol = :symbol"),
            {"symbol": symbol},
        ).scalar_one()

        insert_in_chunks(connection, date_insert, date_records)
        insert_in_chunks(connection, datetime_insert, datetime_records)

        fact_records = []
        for row in frame.itertuples(index=False):
            fact_records.append(
                {
                    "symbol_id": symbol_id,
                    "datetime_id": int(row.datetime_id),
                    "interval": interval,
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": float(row.volume),
                    "quote_asset_volume": float(row.quote_asset_volume),
                    "num_trades": int(row.num_trades),
                    "taker_buy_base": float(row.taker_buy_base),
                    "taker_buy_quote": float(row.taker_buy_quote),
                }
            )
        insert_in_chunks(connection, fact_upsert, fact_records)

    print(f"Loaded {len(frame):,} rows for {symbol}")


def main() -> None:
    engine = create_engine(database_url(), pool_pre_ping=True)
    parquet_files = sorted(DATA_DIR.glob("*_30m.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No Parquet files found in {DATA_DIR}")
    for parquet_path in parquet_files:
        load_file(engine, parquet_path)


if __name__ == "__main__":
    main()
