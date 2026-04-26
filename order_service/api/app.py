from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import psycopg
import pandas as pd
import os
import time
import pika
import json
import requests as http_requests
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

RABBITMQ_CONFIG = {
    "host": os.environ.get("RABBITMQ_HOST", "rabbitmq"),
    "credentials": pika.PlainCredentials(
        os.environ.get("RABBITMQ_USER", "user"),
        os.environ.get("RABBITMQ_PASS", "password"),
    ),
}

# WebSocket Server URL (Option 4)
WS_SERVER_URL = os.environ.get("WS_SERVER_URL", "http://websocket-server:5002")

# =============================================
# HELPER
# =============================================
def convert_value(v):
    if isinstance(v, Decimal):
        return float(v)
    return v

def get_mysql_connection(retries=5, delay=5):
    for attempt in range(1, retries + 1):
        try:
            conn = mysql.connector.connect(**MYSQL_CONFIG)
            print(f"[INFO] MySQL connected on attempt {attempt}")
            return conn
        except Exception as e:
            print(f"[WARN] MySQL not ready ({attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
    return None

def get_postgres_connection(retries=5, delay=5):
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg.connect(**POSTGRES_CONFIG)
            print(f"[INFO] Postgres connected on attempt {attempt}")
            return conn
        except Exception as e:
            print(f"[WARN] Postgres not ready ({attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
    return None

def publish_to_rabbitmq(message: dict):
    try:
        conn = pika.BlockingConnection(pika.ConnectionParameters(**RABBITMQ_CONFIG))
        channel = conn.channel()
        channel.queue_declare(queue="order_queue", durable=True)
        channel.basic_publish(
            exchange="",
            routing_key="order_queue",
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        conn.close()
        print(f"[INFO] Published to RabbitMQ: {message}")

        # Notify WebSocket server for real-time dashboard (Option 4)
        try:
            http_requests.post(
                f"{WS_SERVER_URL}/notify/new_order",
                json=message,
                timeout=2,
            )
            print(f"[INFO] Notified WebSocket server")
        except Exception as ws_err:
            print(f"[WARN] WebSocket notify failed (non-critical): {ws_err}")

    except Exception as e:
        print(f"[WARN] RabbitMQ publish failed: {e}")


# =============================================
# POST /api/orders — Tạo đơn hàng mới
# =============================================
@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    user_id    = data.get("user_id")
    product_id = data.get("product_id")
    quantity   = data.get("quantity", 1)

    if not user_id or not product_id:
        return jsonify({"error": "user_id and product_id are required"}), 400

    conn = get_mysql_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 503

    try:
        cursor = conn.cursor()

        # Tính total_price đơn giản: quantity * 100000 (giả định đơn giá)
        total_price = quantity * 100000

        cursor.execute(
            """
            INSERT INTO orders (user_id, product_id, quantity, total_price, status)
            VALUES (%s, %s, %s, %s, 'PENDING')
            """,
            (user_id, product_id, quantity, total_price),
        )
        conn.commit()
        order_id = cursor.lastrowid

        # Gửi message vào RabbitMQ để worker xử lý
        publish_to_rabbitmq({
            "order_id":   order_id,
            "user_id":    user_id,
            "product_id": product_id,
            "quantity":   quantity,
            "amount":     total_price,
        })

        return jsonify({
            "message":  "Order created successfully",
            "order_id": order_id,
            "status":   "PENDING",
        }), 201

    except Exception as e:
        print(f"[ERROR] create_order: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# =============================================
# GET /api/orders — Lấy danh sách đơn hàng
# =============================================
@app.route("/api/orders", methods=["GET"])
def get_orders():
    try:
        page  = max(1, int(request.args.get("page", 1)))
        limit = min(100, max(1, int(request.args.get("limit", 10))))
    except ValueError:
        return jsonify({"error": "page and limit must be integers"}), 400

    offset = (page - 1) * limit

    conn = get_mysql_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 503

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, user_id, product_id, quantity, total_price, status, created_at FROM orders ORDER BY id DESC LIMIT %s OFFSET %s",
            (limit, offset),
        )
        orders = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) as total FROM orders")
        total = cursor.fetchone()["total"]

        # Chuyển Decimal sang float
        for order in orders:
            for k, v in order.items():
                order[k] = convert_value(v)
            # Chuyển datetime sang string
            if order.get("created_at"):
                order["created_at"] = str(order["created_at"])

        return jsonify({
            "page":    page,
            "limit":   limit,
            "total":   total,
            "orders":  orders,
        }), 200

    except Exception as e:
        print(f"[ERROR] get_orders: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# =============================================
# GET /api/report — Báo cáo tổng hợp
# =============================================
@app.route("/api/report", methods=["GET"])
def generate_report():
    my_conn = get_mysql_connection()
    pg_conn = get_postgres_connection()

    if not my_conn or not pg_conn:
        return jsonify({"error": "Service Unavailable: Database connection failed"}), 503

    try:
        query_mysql = "SELECT id as order_id, user_id, product_id, quantity, status as web_status FROM orders ORDER BY id DESC LIMIT 100"
        df_mysql = pd.read_sql(query_mysql, my_conn)

        query_postgres = "SELECT order_id, user_id FROM transactions"
        df_postgres = pd.read_sql(query_postgres, pg_conn)

        df_merged = pd.merge(df_mysql, df_postgres, on="order_id", how="left")
        df_merged.fillna("", inplace=True)

        return jsonify({
            "total_orders_analyzed": len(df_merged),
            "recent_orders":         df_merged.to_dict(orient="records"),
        }), 200

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if my_conn: my_conn.close()
        if pg_conn: pg_conn.close()


# =============================================
# GET /api/products — Danh sách sản phẩm (Option 5)
# =============================================
@app.route("/api/products", methods=["GET"])
def get_products():
    """Lấy danh sách sản phẩm từ MySQL cho Client Storefront."""
    try:
        limit = min(200, max(1, int(request.args.get("limit", 50))))
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        return jsonify({"error": "limit and offset must be integers"}), 400

    conn = get_mysql_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 503

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, price, stock FROM products ORDER BY id ASC LIMIT %s OFFSET %s",
            (limit, offset),
        )
        products = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) as total FROM products")
        total = cursor.fetchone()["total"]

        # Convert Decimal to float
        for p in products:
            for k, v in p.items():
                p[k] = convert_value(v)

        return jsonify({
            "products": products,
            "total": total,
            "limit": limit,
            "offset": offset,
        }), 200

    except Exception as e:
        print(f"[ERROR] get_products: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# =============================================
# HEALTH CHECK
# =============================================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "order-api"}), 200


# =============================================
# MAIN
# =============================================
if __name__ == "__main__":
    print("[INFO] Initializing Order API...")
    app.run(host="0.0.0.0", port=5000)
