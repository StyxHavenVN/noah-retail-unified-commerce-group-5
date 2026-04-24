import os
import time
import shutil
import csv
import mysql.connector
from mysql.connector import Error

INPUT_DIR = "/app/input"
PROCESSED_DIR = "/app/processed"

# --- SỬA Ở ĐÂY: Đọc cấu hình từ biến môi trường của Docker Compose ---
DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "mysql-db"),   
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "rootpassword"),
    "database": os.environ.get("MYSQL_DATABASE", "noah_web_store"),
    "port": int(os.environ.get("MYSQL_PORT", 3306))
}

# --- KẾT NỐI DB (RETRY) ---
def connect_db():
    while True:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                print("✅ Connected to MySQL")
                return conn
        except Error as e:
            print(f"⏳ Waiting DB... {e}")
            time.sleep(5)

# --- XỬ LÝ FILE ---
def process_file(filepath, conn):
    filename = os.path.basename(filepath)
    print(f"⚡ Processing: {filename}")

    processed = 0
    skipped = 0

    try:
        cursor = conn.cursor()

        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    product_id = int(row['product_id'])
                    quantity = int(row['quantity'])

                    if quantity < 0:
                        raise ValueError("Negative stock")

                    cursor.execute(
                        "UPDATE products SET stock = %s WHERE id = %s",
                        (quantity, product_id)
                    )

                    processed += 1

                except Exception as e:
                    skipped += 1
                    print(f"[SKIPPED] {row} -> {e}")

        conn.commit()
        cursor.close()
        print(f"[INFO] Processed {processed} records. Skipped {skipped} invalid records.")

    except Exception as e:
        print(f"❌ File error: {e}")

    finally:
        # Luôn move để tránh loop vô hạn
        shutil.move(filepath, os.path.join(PROCESSED_DIR, filename))
        print(f"📦 Moved {filename} to processed")

# --- WATCHER ---
def start():
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    conn = connect_db()

    print("👀 Watching /input...")

    while True:
        files = os.listdir(INPUT_DIR)

        for file in files:
            if file.endswith(".csv"):
                process_file(os.path.join(INPUT_DIR, file), conn)

        time.sleep(5)

if __name__ == "__main__":
    start()