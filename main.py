import requests
import polars as pl
import sqlite3
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

API_URL  = "https://openlibrary.org/subjects/children.json?limit=1000"
DB_PATH  = Path("kids_library.db")
LOG_FILE = "pipeline.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)


def extract(url: str) -> List[Dict[str, Any]]:
    logging.info(f"Pulling data from: {url}")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        sys.exit(1)

    works = resp.json().get("works", [])
    if not isinstance(works, list):
        logging.error(f"Unexpected response format: {type(works)}")
        sys.exit(1)

    logging.info(f"Got {len(works)} records.")
    return works


def transform(data: List[Dict[str, Any]]) -> pl.DataFrame:
    logging.info("Transforming...")

    df = pl.DataFrame(data)

    df_clean = (
        df.select(["title", "first_publish_year"])
        .with_columns(
            pl.col("title").str.strip_chars().alias("book_title"),
            pl.col("first_publish_year").cast(pl.Int64, strict=False),
            pl.lit(datetime.now().strftime("%Y-%m-%d %H:%M:%S")).alias("extracted_at"),
        )
        .select(["book_title", "first_publish_year", "extracted_at"])
        .filter(pl.col("book_title").is_not_null() & (pl.col("book_title") != ""))
        .unique(subset=["book_title"], keep="first")
        .sort("first_publish_year", descending=True, nulls_last=True)
    )

    logging.info(f"{df_clean.height} books ready.")
    return df_clean


def load(df: pl.DataFrame, db_path: Path):
    logging.info(f"Writing to SQLite: {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("DROP TABLE IF EXISTS kids_books")
            cur.execute("""
                CREATE TABLE kids_books (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_title   TEXT    NOT NULL,
                    publish_year INTEGER,
                    extracted_at TEXT    NOT NULL
                )
            """)
            cur.executemany(
                "INSERT INTO kids_books (book_title, publish_year, extracted_at) VALUES (?, ?, ?)",
                df.rows(),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
        sys.exit(1)

    logging.info(f"Loaded {df.height} rows -> {db_path}")


if __name__ == "__main__":
    start = datetime.now()

    raw      = extract(API_URL)
    clean_df = transform(raw)
    load(clean_df, DB_PATH)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nDone! {clean_df.height} books loaded in {elapsed:.1f}s")
    print(f"  SQLite -> {DB_PATH.resolve()}")