import pika
import time
import json
import os
import mysql.connector
import psycopg2

# =============================================
# CẤU HÌNH KẾT NỐI
# =============================================
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.environ.get("RABBITMQ_PASS", "password")
QUEUE_NAME = "order_queue"

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
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "password"),
    "dbname": os.environ.get("POSTGRES_DB", "noah_finance"),
}


# =============================================
# MYSQL RETRY
# =============================================
def get_mysql_connection(retries=10, delay=5):   # FIX: tăng retries từ 5 lên 10
    for attempt in range(1, retries + 1):
        try:
            conn = mysql.connector.connect(**MYSQL_CONFIG)
            print(f"[INFO] MySQL connected (attempt {attempt})")
            return conn
        except mysql.connector.Error as e:
            print(f"[WARN] MySQL not ready ({attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
    raise Exception("[ERROR] Cannot connect to MySQL after retries")


def get_postgres_connection(retries=10, delay=5):   # FIX: tăng retries từ 5 lên 10
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(**POSTGRES_CONFIG)
            print(f"[INFO] PostgreSQL connected (attempt {attempt})")
            return conn
        except psycopg2.OperationalError as e:
            print(f"[WARN] PostgreSQL not ready ({attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
    raise Exception("[ERROR] Cannot connect to PostgreSQL after retries")


# =============================================
# PERSISTENT DB CONNECTIONS (dùng chung, không mở/đóng mỗi message)
# =============================================
# FIX: Khởi tạo 1 lần ở cấp module, callback dùng lại
# => Tránh 40.000 lần handshake TCP với 20.000 đơn hàng
mysql_conn = None
postgres_conn = None

def init_db_connections():
    global mysql_conn, postgres_conn
    mysql_conn    = get_mysql_connection()
    postgres_conn = get_postgres_connection()


# =============================================
# INIT POSTGRES
# =============================================
def init_postgres():
    # FIX: dùng persistent connection thay vì mở connection mới
    cursor = postgres_conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          SERIAL PRIMARY KEY,
            order_id    INT UNIQUE, 
            user_id     INT NOT NULL,
            product_id  INT NOT NULL,
            quantity    INT NOT NULL,
            synced_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    postgres_conn.commit()
    cursor.close()
    print("[INFO] PostgreSQL initialized")


# =============================================
# CALLBACK
# =============================================
def callback(ch, method, properties, body):
    try:
        order = json.loads(body.decode())
        order_id = order["order_id"]

        print(f"[INFO] Received Order #{order_id}: {order}")

        time.sleep(2)

        # INSERT POSTGRES (HANDLE DUPLICATE)
        # FIX: dùng persistent postgres_conn, không gọi get_postgres_connection()
        pg_cursor = postgres_conn.cursor()
        try:
            pg_cursor.execute(
                """INSERT INTO transactions (order_id, user_id, product_id, quantity)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (order_id) DO NOTHING""",   # FIX: thêm ON CONFLICT tường minh
                (order["order_id"], order["user_id"], order["product_id"], order["quantity"]),
            )
            postgres_conn.commit()
        except Exception as e:
            postgres_conn.rollback()   # FIX: rollback khi lỗi tránh connection bị treo
            print(f"[WARN] Duplicate or insert error: {e}")
        finally:
            pg_cursor.close()

        print(f"[INFO] Order #{order_id} inserted to PostgreSQL")

        # UPDATE MYSQL (CHECK EXIST)
        # FIX: dùng persistent mysql_conn, không gọi get_mysql_connection()
        my_cursor = mysql_conn.cursor()
        my_cursor.execute(
            "UPDATE orders SET status = 'COMPLETED' WHERE id = %s",
            (order_id,),
        )

        if my_cursor.rowcount == 0:
            raise Exception(f"Order {order_id} not found in MySQL")

        mysql_conn.commit()
        my_cursor.close()

        print(f"[INFO] Order #{order_id} updated to COMPLETED")

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[INFO] Order #{order_id} synced. Notification sent to user.")

    except json.JSONDecodeError as e:
        # FIX: JSON sai format -> requeue=False, không loop vô tận
        print(f"[ERROR] Invalid JSON, discarding message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    except KeyError as e:
        # FIX: thiếu field -> requeue=False, data rác không thể sửa được
        print(f"[ERROR] Missing field {e}, discarding message")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    except Exception as e:
        # Lỗi tạm thời (DB timeout) -> requeue=True, thử lại được
        print(f"[ERROR] Failed to process order: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


# =============================================
# CONSUMER
# =============================================
def start_consuming():
    print("[INFO] Order Worker starting...")

    # FIX: bỏ time.sleep(30) cứng, dùng retry loop trong get_*_connection()
    init_db_connections()
    init_postgres()

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        RABBITMQ_HOST, 5672, "/", credentials,
        heartbeat=600,                    # FIX: giữ kết nối không bị timeout
        blocked_connection_timeout=300,
    )

    # FIX: retry kết nối RabbitMQ thay vì crash ngay
    connection = None
    for attempt in range(1, 11):
        try:
            connection = pika.BlockingConnection(parameters)
            print(f"[INFO] RabbitMQ connected (attempt {attempt})")
            break
        except Exception as e:
            print(f"[WARN] RabbitMQ not ready ({attempt}/10): {e}")
            time.sleep(5)

    if connection is None:
        raise Exception("[ERROR] Cannot connect to RabbitMQ after retries")

    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print(f"[*] Worker ready. Listening on queue '{QUEUE_NAME}'")
    channel.start_consuming()


if __name__ == "__main__":
    start_consuming()
