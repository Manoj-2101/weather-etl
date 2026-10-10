import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = (f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
       f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")

with create_engine(url).connect() as c:
    print("Total rows:", c.execute(text("SELECT COUNT(*) FROM fact_weather")).scalar())

    print("\nDate range and cities:")
    print(" ", c.execute(text(
        "SELECT MIN(weather_date), MAX(weather_date), COUNT(DISTINCT city_id) FROM fact_weather"
    )).fetchone())

    print("\nTables in the database:")
    for r in c.execute(text("SHOW TABLES")):
        print(" ", r[0])

    print("\nColumns:")
    for r in c.execute(text("DESCRIBE fact_weather")):
        print(" ", r[0], r[1])

    print("\nNewest 3 rows:")
    for r in c.execute(text("SELECT * FROM fact_weather ORDER BY 1 DESC LIMIT 3")):
        print(" ", r)