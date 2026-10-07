import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def get_engine():
    url = (
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    return create_engine(url)


def load_to_mysql(df):
    engine = get_engine()
    with engine.begin() as conn:
        # 1. make sure every city exists in dim_city
        for city in df["city"].unique():
            conn.execute(
                text("INSERT IGNORE INTO dim_city (city_name) VALUES (:c)"),
                {"c": city},
            )

        # 2. look up city ids
        rows = conn.execute(text("SELECT city_id, city_name FROM dim_city")).fetchall()
        city_ids = {name: cid for cid, name in rows}

        # 3. upsert facts (safe to re-run)
        sql = text("""
            INSERT INTO fact_weather
                (city_id, weather_date, temp_max_c, temp_min_c, rainfall_mm, wind_max_kmh)
            VALUES (:city_id, :d, :tmax, :tmin, :rain, :wind)
            ON DUPLICATE KEY UPDATE
                temp_max_c = VALUES(temp_max_c),
                temp_min_c = VALUES(temp_min_c),
                rainfall_mm = VALUES(rainfall_mm),
                wind_max_kmh = VALUES(wind_max_kmh)
        """)
        for r in df.itertuples(index=False):
            conn.execute(sql, {
                "city_id": city_ids[r.city],
                "d": r.date,
                "tmax": None if pd.isna(r.temp_max_c) else float(r.temp_max_c),
                "tmin": None if pd.isna(r.temp_min_c) else float(r.temp_min_c),
                "rain": None if pd.isna(r.rainfall_mm) else float(r.rainfall_mm),
                "wind": None if pd.isna(r.wind_max_kmh) else float(r.wind_max_kmh),
            })
    print(f"Loaded {len(df)} rows into MySQL")


if __name__ == "__main__":
    from etl.transform import transform_all
    load_to_mysql(transform_all())