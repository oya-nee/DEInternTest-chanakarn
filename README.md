# 1. Understand what data engineering is and what it is for.
Data Engineering เป็นการทำให้ข้อมูลดิบกลายเป็นข้อมูลที่พร้อมใช้งาน เพื่อเปลี่ยนข้อมูลดิบให้กลายเป็นข้อมูลที่สะอาด และพร้อมสำหรับการนำไปใช้งานต่อ เพื่อให้ Data Scientists หรือ Analysts สามารถเข้าถึงข้อมูลที่มีคุณภาพได้ทันทีโดยไม่ต้องเสียเวลาคลีนข้อมูลเอง และช่วยให้องค์กรตัดสินใจด้วยข้อมูลได้อย่างแม่นยำและรวดเร็ว

# 2. Basic knowledge that data engineer needs to know
Python — pipeline, DataFrame ( pandas / polars ), API / database

SQL — ต้องเข้าใจ JOIN, Window Functions, Query Optimization , ออกแบบ Schema 

Distributed Computing — เข้าใจว่า Spark หรือ Flink ทำงานแบบ Master-Worker อย่างไร / Batch Processing / Streaming

Pipeline Orchestration —  Apache Airflow ที่ใช้ตั้งเวลาและจัดลำดับการทำงานของ pipeline แทนการรัน script 

Data Modeling — ออกแบบ Data Warehouse / Star Schema/  fact table / dimension table 


# 3. ETL Pipeline — Kids Books
เอาข้อมูลมาจาก Open Library API โดยไม่ต้องขอ API key 

## a) Extract
API_URL = "https://openlibrary.org/subjects/children.json?limit=1000"

resp = requests.get(url, timeout=30)

resp.raise_for_status()

works = resp.json().get("works", [])

เรียก HTTP GET ไปที่ Open Library แล้วดึง field works ออกมาจาก JSON response ตั้ง timeout=30 


## b) Transform
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

เลือก 2 column,ทำ strip whitespace หัวท้ายออก, cast ปีเป็น Int64 แบบ strict=False เพื่อไม่ crash ถ้าปีเป็น null, เพิ่ม extracted_at ไว้ tracking และกรอง null/empty ออกก่อน dedup



## c) Load

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


โครงสร้างไฟล์.

├── main.py            # ETL pipeline หลัก

├── queries.sql        # SQL queries สำหรับวิเคราะห์ข้อมูล

├── kids_library.db    # SQLite database (output)

├── pipeline.log       # log การทำงานของ pipeline

├── requirements.txt

└── README.md


### วิธีรัน (ใช้Terminalค่ะ)

bashpip install -r requirements.txt

python main.py
<img width="1322" height="235" alt="image" src="https://github.com/user-attachments/assets/f2d7c8af-0b48-4a0e-95bd-b72e869477c4" />



  
  
### Tech Stack
Python 3.x

Polars — Transform DataFrame

SQLite — RDBMS ปลายทาง

Requests — เรียก API

## ตัวอย่าง queries ที่ได้
<img width="717" height="323" alt="Screenshot 2026-03-08 145853" src="https://github.com/user-attachments/assets/b15e36e1-cca3-43da-b642-e78adcb0257c" />
<img width="716" height="425" alt="Screenshot 2026-03-08 145821" src="https://github.com/user-attachments/assets/56ae97bd-4006-4e08-89b1-090654362197" />
<img width="728" height="443" alt="Screenshot 2026-03-08 145758" src="https://github.com/user-attachments/assets/861dd93e-6ba8-453b-a697-1925a908d3aa" />





### Data Source
- [Open Library](https://openlibrary.org/)
