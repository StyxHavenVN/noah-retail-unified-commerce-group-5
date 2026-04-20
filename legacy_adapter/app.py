import os
import time
import shutil
import csv
import mysql.connector
from mysql.connector import Error

INPUT_DIR = "/app/input"
PROCESSED_DIR = "/app/processed"

DB_CONFIG = {
    "host": "mysql_db",   # nhớ trùng với docker-compose
    "user": "root",
    "password": "rootpassword",
    "database": "noah_web_store"
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
                        "UPDATE products SET quantity = %s WHERE product_id = %s",
                        (quantity, product_id)
                    )

                    processed += 1

                except Exception as e:
                    skipped += 1
                    print(f"[SKIPPED] {row} -> {e}")

        conn.commit()

        print(f"[INFO] Processed {processed} records, Skipped {skipped} records")

    except Exception as e:
        print(f"❌ File error: {e}")

    finally:
        # LUÔN move để tránh loop vô hạn
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