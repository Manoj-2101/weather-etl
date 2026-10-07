# Weather ETL Pipeline

A Python ETL pipeline that extracts daily weather data for five Indian cities from the Open-Meteo REST API, cleans it with Pandas, and loads it into a MySQL star schema. It runs on a daily schedule with logging and retry handling.

## Architecture

```
Open-Meteo API -> Extract (requests) -> Transform (Pandas) -> Load (MySQL) -> Power BI (planned)
                                                                  ^
                              Scheduled daily (Windows Task Scheduler)
```

## Features

- **Extract:** fetches daily max/min temperature, rainfall and wind speed for Bengaluru, Mumbai, Delhi, Chennai and Kolkata, with retry and backoff on API failures. Raw JSON is saved so the transform can be re-run.
- **Transform:** flattens JSON into a table with Pandas, converts types, handles missing values, removes duplicates and validates that min temperature is not above max.
- **Load:** writes to a star schema (`dim_city`, `fact_weather`) with upserts on a unique key `(city_id, weather_date)`, so re-running never creates duplicates.
- **Operations:** logging to file, one-command run (`python main.py`), daily scheduling through a batch file.

## Tech stack

Python, Requests, Pandas, SQLAlchemy, PyMySQL, MySQL, Windows Task Scheduler, Git

## Setup

1. Clone the repo and create a virtual environment:
```
   git clone https://github.com/Manoj-2101/weather-etl.git
   cd weather-etl
   python -m venv venv
   venv\Scripts\activate
   python -m pip install -r requirements.txt
```
2. Create the database and tables in MySQL (see the schema below).
3. Create a `.env` file in the project root:
```
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=your_user
   DB_PASSWORD=your_password
   DB_NAME=weather_etl
```
4. Run the pipeline:
```
   python main.py
```

## Database schema

```sql
CREATE DATABASE IF NOT EXISTS weather_etl;
USE weather_etl;

CREATE TABLE IF NOT EXISTS dim_city (
    city_id INT AUTO_INCREMENT PRIMARY KEY,
    city_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS fact_weather (
    weather_id INT AUTO_INCREMENT PRIMARY KEY,
    city_id INT NOT NULL,
    weather_date DATE NOT NULL,
    temp_max_c DECIMAL(4,1),
    temp_min_c DECIMAL(4,1),
    rainfall_mm DECIMAL(5,1),
    wind_max_kmh DECIMAL(5,1),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES dim_city(city_id),
    UNIQUE KEY uq_city_date (city_id, weather_date)
);
```

## Project structure

```
weather-etl/
├── etl/
│   ├── config.py      # cities and API settings
│   ├── extract.py     # API calls with retries
│   ├── transform.py   # Pandas cleaning
│   └── load.py        # idempotent MySQL load
├── main.py            # runs all stages with logging
├── run_etl.bat        # entry point for the scheduler
└── requirements.txt
```

## Author

Manoj K N
