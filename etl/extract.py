import json
import logging
import time
from datetime import date

import requests

from etl.config import API_URL, CITIES, DAILY_FIELDS, RAW_DIR


def fetch_city(city, lat, lon, retries=3):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": DAILY_FIELDS,
        "timezone": "Asia/Kolkata",
        "past_days": 7,
        "forecast_days": 1,
    }
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.warning("[%s] attempt %d failed: %s", city, attempt, e)
            time.sleep(2 * attempt)
    raise RuntimeError(f"Could not fetch data for {city} after {retries} attempts")


def extract_all():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for city, (lat, lon) in CITIES.items():
        data = fetch_city(city, lat, lon)
        path = RAW_DIR / f"{city}_{date.today()}.json"
        path.write_text(json.dumps(data, indent=2))
        logging.info("Saved %s", path)


if __name__ == "__main__":
    extract_all()