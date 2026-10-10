import argparse
import logging
import webbrowser
from pathlib import Path

from etl.extract import extract_all
from etl.transform import transform_all
from etl.load import load_to_mysql
from etl.dashboard import build_dashboard

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_FILE = BASE_DIR / "dashboard" / "index.html"

(BASE_DIR / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / "etl.log"),
        logging.StreamHandler(),
    ],
)


def run(open_dashboard: bool = True) -> None:
    logging.info("ETL run started")

    # Extract -> Transform -> Load (a failure here stops the run)
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

    # Dashboard (a failure here does not affect the data already loaded)
    dashboard_ok = False
    try:
        build_dashboard()
        dashboard_ok = True
        logging.info("Dashboard updated")
    except Exception:
        logging.exception("Dashboard update failed (ETL data is safe)")

    if dashboard_ok and open_dashboard:
        try:
            if DASHBOARD_FILE.exists():
                webbrowser.open(DASHBOARD_FILE.as_uri())
                logging.info("Opened dashboard in browser: %s", DASHBOARD_FILE)
            else:
                logging.warning("Dashboard file not found: %s", DASHBOARD_FILE)
        except Exception:
            logging.exception("Could not open dashboard in browser")

    if dashboard_ok:
        logging.info("ETL run completed successfully")
    else:
        logging.warning("ETL run completed, but the dashboard update failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weather ETL pipeline")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't open the dashboard in a browser (use for scheduled runs)",
    )
    args = parser.parse_args()
    run(open_dashboard=not args.no_open)