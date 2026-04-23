from flask import Flask, jsonify
import pandas as pd
import mysql.connector
import psycopg2

app = Flask(__name__)

MYSQL_CONFIG = {
    'host': 'noah_mysql',
    'port': 3306,
    'user': 'root',
    'password': 'rootpassword',
    'database': 'noah_web_store'
}

POSTGRES_CONFIG = {
    'host': 'noah_postgres',
    'port': 5432,
    'user': 'admin',
    'password': 'adminpassword',
    'database': 'noah_finance'
}

MYSQL_QUERY_PRODUCTS = "SELECT id, name AS product_name FROM products"
MYSQL_QUERY_ORDERS = "SELECT product_id, quantity, total_price FROM orders"
def get_stitched_report():
    try:
        # Kết nối tới MySQL (Chỉ cần 1 kết nối duy nhất)
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        
        df_products = pd.read_sql(MYSQL_QUERY_PRODUCTS, conn)
        df_orders = pd.read_sql(MYSQL_QUERY_ORDERS, conn)
        
        conn.close()

        # KHÂU DỮ LIỆU: id của bảng products gộp với product_id của bảng orders
        merged_df = pd.merge(
            df_products, 
            df_orders, 
            left_on='id', 
            right_on='product_id', 
            how='inner'
        )

        merged_df['total_revenue'] = merged_df['quantity'] * merged_df['total_price']

        return merged_df.to_dict(orient='records')
        
    except Exception as e:
        return {"error": str(e)}
    
@app.route('/api/report', methods=['GET'])
def generate_report():
    data = get_stitched_report()
    
    if isinstance(data, dict) and "error" in data:
        return jsonify({"success": False, "message": data["error"]}), 500
        
    return jsonify({
        "success": True,
        "total_records": len(data),
        "data": data
    }), 200

if __name__ == '__main__':
    # Chạy ở port 5000 để khớp với mạng internal của Docker
    app.run(host='0.0.0.0', port=5000)