from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import psycopg
import pandas as pd
import os
import time
from decimal import Decimal

app = Flask(__name__)
CORS(app)

# =============================================
# CẤU HÌNH KẾT NỐI (Lấy từ Docker Env)
# =============================================
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "mysql-db"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "password"),
    "database": os.environ.get("MYSQL_DATABASE", "noah_retail"),
}

POSTGRES_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "postgres-db"),
    "port": int(os.environ.get("POSTGRES_PORT", 5432)),
    "user": os.environ.get("POSTGRES_USER", "finance_user"),
    "password": os.environ.get("POSTGRES_PASSWORD", "finance_password"),
    "dbname": os.environ.get("POSTGRES_DB", "finance_db"),
}

# =============================================
# HELPER: XỬ LÝ DỮ LIỆU SỐ & NULL
# =============================================
def convert_value(v):
    if isinstance(v, Decimal):
        return float(v) # Chuyển Decimal sang float để JSON nhận diện được
    return v

# =============================================
# DATABASE RETRY HELPERS
# =============================================
def get_mysql_connection(retries=5, delay=5):
    for attempt in range(1, retries + 1):
        try:
            conn = mysql.connector.connect(**MYSQL_CONFIG)
            print(f"[INFO] MySQL connected on attempt {attempt}")
            return conn
        except Exception as e:
            print(f"[WARN] MySQL not ready ({attempt}/{retries}): {e}")
            if attempt < retries: time.sleep(delay)
    return None

def get_postgres_connection(retries=5, delay=5):
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg.connect(**POSTGRES_CONFIG)
            print(f"[INFO] Postgres connected on attempt {attempt}")
            return conn
        except Exception as e:
            print(f"[WARN] Postgres not ready ({attempt}/{retries}): {e}")
            if attempt < retries: time.sleep(delay)
    return None

# =============================================
# GET /api/report
# =============================================
@app.route('/api/report', methods=['GET'])
def generate_report():
    my_conn = get_mysql_connection()
    pg_conn = get_postgres_connection()

    if not my_conn or not pg_conn:
        return jsonify({"error": "Service Unavailable: Database connection failed"}), 503

    try:
        # 1. Rút dữ liệu từ MySQL (Limit để đảm bảo hiệu năng)
        query_mysql = "SELECT id as order_id, user_id, product_id, quantity, status as web_status FROM orders ORDER BY id DESC LIMIT 100"
        df_mysql = pd.read_sql(query_mysql, my_conn)

        # 2. Rút dữ liệu từ PostgreSQL
        query_postgres = "SELECT order_id, amount, status as finance_status FROM finance_transactions"
        df_postgres = pd.read_sql(query_postgres, pg_conn)

        # 3. DATA STITCHING (Pandas Merge)
        df_merged = pd.merge(df_mysql, df_postgres, on='order_id', how='left')

        # Xử lý các giá trị trống và số Decimal
        df_merged['amount'] = df_merged['amount'].fillna(0).apply(convert_value)
        df_merged.fillna("", inplace=True)
        
        # 4. TÍNH TOÁN DOANH THU (Aggregation)
        df_revenue = df_merged.groupby('user_id')['amount'].sum().reset_index()
        df_revenue.rename(columns={'amount': 'total_spent'}, inplace=True)

        # Chuyển đổi dữ liệu sang Dictionary để trả về JSON
        report_data = {
            "total_orders_analyzed": len(df_merged),
            "recent_orders": df_merged.to_dict(orient='records'),
            "revenue_by_user": df_revenue.to_dict(orient='records')
        }

        return jsonify(report_data), 200

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if my_conn: my_conn.close()
        if pg_conn: pg_conn.close()

# =============================================
# MAIN
# =============================================
if __name__ == '__main__':
    print("[INFO] Initializing Reporting API...")
    # Chạy ở port 5001 (Khớp với cấu hình Kong và Docker Compose)
    app.run(host='0.0.0.0', port=5001)
