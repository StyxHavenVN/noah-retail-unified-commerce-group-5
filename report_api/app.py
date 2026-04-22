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

MYSQL_QUERY = "SELECT o.id AS order_id, p.name AS product_name, o.status FROM orders o JOIN products p ON o.product_id = p.id WHERE o.status = 'Success'"
POSTGRES_QUERY = "SELECT order_id, quantity, unit_price FROM transactions"

def get_stitched_report():
    try:
        conn_mysql = mysql.connector.connect(**MYSQL_CONFIG)
        df_products = pd.read_sql(MYSQL_QUERY, conn_mysql)
        conn_mysql.close()

        conn_pg = psycopg2.connect(**POSTGRES_CONFIG)
        df_transactions = pd.read_sql(POSTGRES_QUERY, conn_pg)
        conn_pg.close()

        merged_df = pd.merge(df_transactions, df_products, on='order_id', how='inner')

        merged_df['total_revenue'] = merged_df['quantity'] * merged_df['unit_price']

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