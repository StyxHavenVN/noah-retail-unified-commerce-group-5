from flask import Flask, jsonify, request
import pandas as pd
from sqlalchemy import create_engine, text
import os
import time
from datetime import datetime

app = Flask(__name__)

# =============================================
# CẤU HÌNH KẾT NỐI
# =============================================
MYSQL_URL = os.environ.get(
    "MYSQL_URL",
    "mysql+mysqlconnector://root:password@mysql-db:3306/noah_retail"
)

POSTGRES_URL = os.environ.get(
    "POSTGRES_URL",
    "postgresql+psycopg2://postgres:password@postgres-db:5432/noah_finance"
)


# =============================================
# RETRY DB CONNECTION
# =============================================
def get_mysql_engine(retries=10, delay=5):
    for attempt in range(1, retries + 1):
        try:
            engine = create_engine(MYSQL_URL, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[INFO] MySQL connected (attempt {attempt})")
            return engine
        except Exception as e:
            print(f"[WARN] MySQL not ready ({attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
    raise Exception("[ERROR] Cannot connect to MySQL after retries")


def get_postgres_engine(retries=10, delay=5):
    for attempt in range(1, retries + 1):
        try:
            engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[INFO] PostgreSQL connected (attempt {attempt})")
            return engine
        except Exception as e:
            print(f"[WARN] PostgreSQL not ready ({attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
    raise Exception("[ERROR] Cannot connect to PostgreSQL after retries")


# =============================================
# PERSISTENT DB ENGINES
# =============================================
mysql_engine    = None
postgres_engine = None

def init_db_engines():
    global mysql_engine, postgres_engine
    mysql_engine    = get_mysql_engine()
    postgres_engine = get_postgres_engine()


# =============================================
# HEALTH CHECK
# =============================================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "module": "module3_reporting"}), 200


# =============================================
# REPORT ENDPOINT  —  GET /api/report
# =============================================
@app.route("/api/report", methods=["GET"])
def get_report():

    try:
        page      = max(1, int(request.args.get("page", 1)))
        page_size = min(100, max(1, int(request.args.get("page_size", 20))))
    except ValueError:
        return jsonify({"success": False, "message": "page and page_size must be integers"}), 400

    offset = (page - 1) * page_size

    try:
        # ── PHASE 1: EXTRACT ─────────────────────────────────────────────

        # Nguồn 1: MySQL — bảng orders
        try:
            with mysql_engine.connect() as conn:
                df_orders = pd.read_sql(
                    text("""
                        SELECT id          AS order_id,
                               user_id,
                               product_id,
                               quantity,
                               total_price,
                               status
                        FROM   orders
                        ORDER  BY id
                        LIMIT  :limit OFFSET :offset
                    """),
                    conn,
                    params={"limit": page_size, "offset": offset}
                )
                total_count = conn.execute(
                    text("SELECT COUNT(*) FROM orders")
                ).scalar()
            print(f"[INFO] Loaded {len(df_orders)} orders from MySQL (page {page})")
        except Exception as e:
            print(f"[ERROR] MySQL read failed: {e}")
            return jsonify({"success": False, "message": f"MySQL error: {str(e)}"}), 500

        # Nguồn 2: PostgreSQL — bảng transactions
        try:
            with postgres_engine.connect() as conn:
                df_transactions = pd.read_sql(
                    text("""
                        SELECT order_id,
                               'COMPLETED' AS finance_status
                        FROM   transactions
                    """),
                    conn
                )
            print(f"[INFO] Loaded {len(df_transactions)} transactions from PostgreSQL")
        except Exception as e:
            print(f"[ERROR] PostgreSQL read failed: {e}")
            return jsonify({"success": False, "message": f"PostgreSQL error: {str(e)}"}), 500

        # ── PHASE 2: TRANSFORM (DATA STITCHING) ──────────────────────────
        try:
            merged_df = pd.merge(
                df_orders,
                df_transactions,
                on="order_id",
                how="left"
            )

            # Tính unit_price = total_price / quantity
            merged_df["unit_price"] = merged_df.apply(
                lambda r: round(float(r["total_price"]) / int(r["quantity"]), 2)
                if r["quantity"] and int(r["quantity"]) > 0 else 0.0,
                axis=1
            )

            # Tạo product_name từ product_id
            merged_df["product_name"] = merged_df["product_id"].apply(
                lambda x: f"Sản phẩm {x}"
            )

            print(f"[INFO] Data stitching OK — {len(merged_df)} records")
        except Exception as e:
            print(f"[ERROR] Data stitching failed: {e}")
            return jsonify({"success": False, "message": f"Stitching error: {str(e)}"}), 500

        # ── PHASE 3: BUILD RESPONSE ───────────────────────────────────────
        data_list = []
        skipped = 0
        for _, row in merged_df.iterrows():
            try:
                data_list.append({
                    # Fields cho Streamlit dashboard.py
                    "order_id":       int(row["order_id"]),
                    "product_name":   str(row["product_name"]),
                    "status":         str(row.get("finance_status") or row["status"]),
                    "quantity":       int(row["quantity"]),
                    "unit_price":     round(float(row["unit_price"]), 2),
                    "total_revenue":  round(float(row["total_price"]), 2),
                    # Fields thêm cho dashboard.html
                    "user_id":        int(row["user_id"]),
                    "product_id":     int(row["product_id"]),
                    "web_status":     str(row["status"]),
                    "finance_status": str(row.get("finance_status") or "CHỜ"),
                })
            except Exception as e:
                print(f"[WARN] Skipped bad row: {e}")
                skipped += 1
                continue

        total_pages = max(1, -(-total_count // page_size))
        print(f"[INFO] Processed {len(data_list)} records. Skipped {skipped} invalid.")

        return jsonify({
            # ── Streamlit format ──
            "success":       True,
            "total_records": total_count,
            "data":          data_list,

            # ── dashboard.html format (giữ tương thích) ──
            "status":                "success",
            "total_orders_analyzed": total_count,
            "revenue_by_user": [
                {
                    "customer_id":   int(row["user_id"]),
                    "customer_name": f"User {int(row['user_id'])}",
                    "total_revenue": round(float(row["total_price"]), 2),
                    "total_orders":  1,
                }
                for _, row in merged_df.iterrows()
            ],
            "recent_orders": [
                {
                    "order_id":       int(row["order_id"]),
                    "product_id":     int(row["product_id"]),
                    "web_status":     str(row["status"]),
                    "finance_status": str(row.get("finance_status") or "CHỜ"),
                }
                for _, row in merged_df.head(10).iterrows()
            ],
            "pagination": {
                "page":        page,
                "page_size":   page_size,
                "total_count": total_count,
                "total_pages": total_pages,
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        }), 200

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# SUMMARY ENDPOINT  —  GET /api/report/summary
# =============================================
@app.route("/api/report/summary", methods=["GET"])
def get_summary():
    try:
        with mysql_engine.connect() as conn:
            total_orders   = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
            total_revenue  = conn.execute(text("SELECT COALESCE(SUM(total_price), 0) FROM orders")).scalar()
            pending_orders = conn.execute(text("SELECT COUNT(*) FROM orders WHERE status = 'PENDING'")).scalar()

        with postgres_engine.connect() as conn:
            total_customers = conn.execute(text("SELECT COUNT(DISTINCT user_id) FROM transactions")).scalar()

        print(f"[INFO] Summary fetched OK")

        return jsonify({
            "status": "success",
            "summary": {
                "total_orders":    total_orders,
                "total_revenue":   round(float(total_revenue), 2),
                "pending_orders":  pending_orders,
                "total_customers": total_customers,
                "generated_at":    datetime.utcnow().isoformat() + "Z"
            }
        }), 200

    except Exception as e:
        print(f"[ERROR] Summary failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================
# MAIN
# =============================================
if __name__ == "__main__":
    print("[INFO] Report API starting...")
    init_db_engines()
    app.run(host="0.0.0.0", port=5001, debug=False)
