"""Validate the portfolio Parquet datasets and report time-series gaps."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
EXPECTED_INTERVAL = timedelta(minutes=30)

REQUIRED_COLUMNS = [
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


def validate_file(path: Path) -> dict[str, object]:
    frame = pd.read_parquet(path)
    missing_columns = sorted(set(REQUIRED_COLUMNS).difference(frame.columns))
    if missing_columns:
        raise ValueError(f"{path.name}: missing columns {missing_columns}")

    frame["open_time"] = pd.to_datetime(frame["open_time"])
    numeric = frame[NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    invalid_ohlc = (
        (numeric["high"] < numeric[["open", "close", "low"]].max(axis=1))
        | (numeric["low"] > numeric[["open", "close", "high"]].min(axis=1))
    )
    gaps = frame["open_time"].sort_values().diff()
    gap_rows = []
    for index in gaps[gaps > EXPECTED_INTERVAL].index:
        gap_end = frame.loc[index, "open_time"]
        gap_start = gap_end - gaps.loc[index]
        gap_rows.append(
            {
                "after": gap_start,
                "before": gap_end,
                "missing_candles": int(gaps.loc[index] / EXPECTED_INTERVAL) - 1,
            }
        )

    result = {
        "file": path.name,
        "rows": len(frame),
        "start": frame["open_time"].min(),
        "end": frame["open_time"].max(),
        "duplicates": int(frame.duplicated(["symbol", "open_time"]).sum()),
        "missing_values": int(frame[REQUIRED_COLUMNS].isna().sum().sum()),
        "numeric_parse_errors": int(numeric.isna().sum().sum()),
        "negative_rows": int((numeric < 0).any(axis=1).sum()),
        "invalid_ohlc_rows": int(invalid_ohlc.sum()),
        "gaps": gap_rows,
    }

    critical_fields = [
        "duplicates",
        "missing_values",
        "numeric_parse_errors",
        "negative_rows",
        "invalid_ohlc_rows",
    ]
    if any(result[field] for field in critical_fields):
        raise ValueError(f"{path.name}: critical validation failure: {result}")
    return result


def main() -> None:
    files = sorted(DATA_DIR.glob("*_30m.parquet"))
    if not files:
        raise FileNotFoundError(f"No Parquet files found in {DATA_DIR}")

    for path in files:
        result = validate_file(path)
        print(
            f"{result['file']}: {result['rows']:,} rows, "
            f"{result['start']} to {result['end']}"
        )
        for gap in result["gaps"]:
            print(
                "  WARNING: "
                f"{gap['missing_candles']} missing 30-minute candles between "
                f"{gap['after']} and {gap['before']}"
            )


if __name__ == "__main__":
    main()
