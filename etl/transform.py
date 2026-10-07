import json
from datetime import date
from pathlib import Path

import pandas as pd

from etl.config import RAW_DIR

PROCESSED_DIR = Path("data/processed")

COLUMN_MAP = {
    "time": "date",
    "temperature_2m_max": "temp_max_c",
    "temperature_2m_min": "temp_min_c",
    "precipitation_sum": "rainfall_mm",
    "wind_speed_10m_max": "wind_max_kmh",
}


def load_raw_file(path):
    data = json.loads(path.read_text())
    df = pd.DataFrame(data["daily"])          # lists -> table
    df["city"] = path.stem.split("_")[0]      # "Bengaluru_2026-10-06" -> "Bengaluru"
    return df


def clean(df):
    df = df.rename(columns=COLUMN_MAP)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    numeric_cols = ["temp_max_c", "temp_min_c", "rainfall_mm", "wind_max_kmh"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    # drop rows with no temperature at all (useless for analysis)
    df = df.dropna(subset=["temp_max_c", "temp_min_c"], how="all")

    # sanity check: min temperature can't be higher than max
    df = df[df["temp_min_c"] <= df["temp_max_c"]]

    # same city + date should appear only once
    df = df.drop_duplicates(subset=["city", "date"], keep="last")

    return df[["city", "date"] + numeric_cols].reset_index(drop=True)


def transform_all():
    files = list(RAW_DIR.glob(f"*_{date.today()}.json"))
    if not files:
        raise FileNotFoundError("No raw files for today. Run etl.extract first.")

    df = pd.concat([load_raw_file(f) for f in files], ignore_index=True)
    df = clean(df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "weather_clean.csv"
    df.to_csv(out, index=False)
    print(f"Cleaned {len(df)} rows -> {out}")
    return df


if __name__ == "__main__":
    print(transform_all().head(10))