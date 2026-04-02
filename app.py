# app.py
import os
import socket
from flask import Flask, jsonify
app = Flask(__name__)
@app.route('/')
def info():
 # Lấy Hostname để xem code đang chạy trên máy nào (Máy thật hay Container)
 container_id = socket.gethostname()

 # Lấy biến môi trường (Config) từ bên ngoài truyền vào
 env_name = os.getenv('ENV_NAME', 'Local Environment')
 return jsonify({
 "status": "Success",
 "message": "Version 2.0 Updated",
 "running_on_container_id": container_id,
 "environment_config": env_name
 })
if __name__ == '__main__':
 # host='0.0.0.0' là BẮT BUỘC để container mở cửa cho bên ngoài truy cập
 app.run(host='0.0.0.0', port=5000)