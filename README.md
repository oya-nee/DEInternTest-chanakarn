Kids Books ETL Pipeline
โปรเจกต์นี้ทำขึ้นเพื่อตอบโจทย์ DE Intern Test — ดึงข้อมูลหนังสือเด็กจาก Open Library API แล้วเก็บลง SQLite

1. Data Engineering คืออะไร และมีไว้เพื่ออะไร
Data Engineering คือการสร้างระบบที่ทำให้ข้อมูลดิบกลายเป็นข้อมูลที่พร้อมใช้งาน
ปัญหาจริงที่ DE แก้คือ ข้อมูลในองค์กรมักกระจัดกระจายอยู่หลายที่ ทั้ง API ภายนอก, database หลายตัว, ไฟล์ Excel ของแต่ละทีม ข้อมูลพวกนี้ยังดิบ ยังสกปรก และยังเชื่อมกันไม่ได้ Data Analyst หรือ Data Scientist จะวิเคราะห์ไม่ได้ถ้าไม่มีใครจัดการตรงนี้
งานหลักของ DE คือออกแบบและดูแล Data Pipeline ซึ่งก็คือระบบที่คอย Extract ข้อมูลจากแหล่งต่างๆ → Transform ให้สะอาดและอยู่ในรูปแบบที่ใช้งานได้ → Load ลงปลายทางที่ทีมอื่นเข้าถึงได้ ที่เรียกกันว่า ETL

2. ความรู้พื้นฐานที่ DE ต้องมี
Python — ใช้เขียน pipeline, จัดการ DataFrame ด้วย pandas หรือ polars, เชื่อมต่อกับ API และ database
SQL — ต้องแม่นกว่าแค่ SELECT ธรรมดา ต้องเข้าใจ JOIN, Window Functions, Query Optimization และออกแบบ Schema ได้
Distributed Computing — เข้าใจว่า Spark หรือ Flink ทำงานแบบ Master-Worker อย่างไร รู้ความต่างระหว่าง Batch Processing กับ Streaming
Pipeline Orchestration — รู้จักเครื่องมืออย่าง Apache Airflow ที่ใช้ตั้งเวลาและจัดลำดับการทำงานของ pipeline แทนการรัน script มือ
Data Modeling — ออกแบบ Data Warehouse ได้ เข้าใจ Star Schema, รู้ว่าควรแยก fact table กับ dimension table ยังไง

3. ETL Pipeline — Kids Books
เลือก Open Library API เพราะเปิดฟรี ไม่ต้องขอ API key และข้อมูลหนังสือเด็กมีมาตั้งแต่ปี 1200 จนถึงปัจจุบัน น่าสนใจในแง่ประวัติศาสตร์วรรณกรรม
a) Extract — ดึงข้อมูลจาก API
python# main.py → def extract()
API_URL = "https://openlibrary.org/subjects/children.json?limit=1000"

resp = requests.get(url, timeout=30)
resp.raise_for_status()
works = resp.json().get("works", [])
เรียก HTTP GET ไปที่ Open Library แล้วดึง field works ออกมาจาก JSON response ตั้ง timeout=30 ไว้เพื่อไม่ให้ pipeline ค้างถ้า API ช้า และ validate ว่า response เป็น list จริงก่อนใช้งานต่อ
b) Transform — ทำความสะอาดข้อมูล
python# main.py → def transform()
df_clean = (
    df.select(["title", "first_publish_year"])
    .with_columns(
        pl.col("title").str.strip_chars().alias("book_title"),
        pl.col("first_publish_year").cast(pl.Int64, strict=False),
        pl.lit(datetime.now().strftime("%Y-%m-%d %H:%M:%S")).alias("extracted_at"),
    )
    .filter(pl.col("book_title").is_not_null() & (pl.col("book_title") != ""))
    .unique(subset=["book_title"], keep="first")
    .sort("first_publish_year", descending=True, nulls_last=True)
)
ขั้นตอนที่ทำในนี้มี 5 อย่าง:

เลือกแค่ 2 column ที่จำเป็น (title, first_publish_year)
strip whitespace หัวท้ายออกจากชื่อหนังสือ
cast ปีเป็น Int64 แบบ strict=False เพื่อไม่ให้ crash ถ้าปีเป็น null
เพิ่ม extracted_at เป็น metadata ว่าดึงข้อมูลมาเมื่อไหร่
กรอง null/empty ออก แล้ว dedup ด้วย unique()

จาก 1,000 records ที่ดึงมา เหลือ 989 หลัง transform
c) Load — เก็บลง SQLite (RDBMS)
python# main.py → def load()
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
ใช้ DROP TABLE IF EXISTS ก่อน CREATE ทุกครั้ง ทำให้รัน pipeline ซ้ำกี่ครั้งก็ได้โดยไม่ duplicate (Idempotent Load) Schema มี Primary Key และ NOT NULL constraint ตาม RDBMS best practice

โครงสร้างไฟล์
.
├── main.py            # ETL pipeline หลัก
├── queries.sql        # SQL queries สำหรับวิเคราะห์ข้อมูล
├── kids_library.db    # SQLite database (output)
├── pipeline.log       # log การทำงานของ pipeline
├── requirements.txt   # dependencies
└── README.md
วิธีรัน
bashpip install -r requirements.txt
python main.py
ผลลัพธ์ที่ได้
Done! 989 books loaded in 4.2s
  SQLite -> /your/path/kids_library.db
Tech Stack

Python 3.x
Polars — DataFrame library สำหรับ transform (เร็วกว่า pandas สำหรับ memory management)
SQLite — RDBMS ปลายทาง
Requests — HTTP client สำหรับเรียก API