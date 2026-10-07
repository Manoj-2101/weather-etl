import logging
from pathlib import Path

from etl.extract import extract_all
from etl.transform import transform_all
from etl.load import load_to_mysql

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/etl.log"),
        logging.StreamHandler(),
    ],
)


def run():
    logging.info("ETL run started")
    try:
        extract_all()
        logging.info("Extract finished")

        df = transform_all()
        logging.info("Transform finished: %d rows", len(df))

        load_to_mysql(df)
        logging.info("Load finished: %d rows", len(df))
    except Exception:
        logging.exception("ETL run failed")
        raise
    logging.info("ETL run completed successfully")


if __name__ == "__main__":
    run()