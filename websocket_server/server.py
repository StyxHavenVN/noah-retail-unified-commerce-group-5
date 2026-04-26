"""
WebSocket Server — Real-Time Event Hub
Sử dụng python-socketio + eventlet để broadcast sự kiện real-time
tới Dashboard và Client Storefront.
"""
import socketio
import eventlet
import os
import json
from flask import Flask, request, jsonify

# =============================================
# CẤU HÌNH
# =============================================
PORT = int(os.environ.get("WS_PORT", 5002))

# Tạo Flask app để nhận HTTP notification từ Order API
flask_app = Flask(__name__)

# Tạo Socket.IO server với CORS cho phép tất cả
sio = socketio.Server(
    cors_allowed_origins="*",
    async_mode="eventlet",
    logger=True,
    engineio_logger=False,
)

# Wrap Flask app với Socket.IO
app = socketio.WSGIApp(sio, flask_app)

# Theo dõi số client đang kết nối
connected_clients = set()


# =============================================
# SOCKET.IO EVENTS
# =============================================
@sio.event
def connect(sid, environ):
    connected_clients.add(sid)
    print(f"[WS] Client connected: {sid} (total: {len(connected_clients)})")
    sio.emit("connection_ack", {
        "message": "Connected to NOAH Real-Time Hub",
        "sid": sid,
        "total_clients": len(connected_clients),
    }, room=sid)


@sio.event
def disconnect(sid):
    connected_clients.discard(sid)
    print(f"[WS] Client disconnected: {sid} (total: {len(connected_clients)})")


@sio.event
def ping_server(sid, data):
    """Health check từ client."""
    sio.emit("pong_server", {"status": "ok"}, room=sid)


# =============================================
# HTTP ENDPOINT — Nhận notification từ Order API
# =============================================
@flask_app.route("/notify/new_order", methods=["POST"])
def notify_new_order():
    """Order API gọi endpoint này khi có đơn hàng mới."""
    data = request.get_json() or {}
    order_id = data.get("order_id", "?")
    user_id = data.get("user_id", "?")
    product_id = data.get("product_id", "?")
    quantity = data.get("quantity", 0)
    amount = data.get("amount", 0)

    event_data = {
        "order_id": order_id,
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity,
        "amount": amount,
        "status": "PENDING",
    }

    # Broadcast tới tất cả client đang kết nối
    sio.emit("new_order", event_data)
    print(f"[WS] Broadcasted new_order #{order_id} to {len(connected_clients)} clients")

    return jsonify({"status": "ok", "broadcasted_to": len(connected_clients)}), 200


@flask_app.route("/notify/order_completed", methods=["POST"])
def notify_order_completed():
    """Worker gọi endpoint này khi đơn hàng hoàn thành."""
    data = request.get_json() or {}
    order_id = data.get("order_id", "?")

    event_data = {
        "order_id": order_id,
        "status": "COMPLETED",
    }

    sio.emit("order_completed", event_data)
    print(f"[WS] Broadcasted order_completed #{order_id}")

    return jsonify({"status": "ok"}), 200


@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "websocket-server",
        "connected_clients": len(connected_clients),
    }), 200


# =============================================
# MAIN
# =============================================
if __name__ == "__main__":
    print(f"[INFO] WebSocket Server starting on port {PORT}...")
    print(f"[INFO] Socket.IO endpoint: ws://0.0.0.0:{PORT}/socket.io/")
    print(f"[INFO] HTTP notify endpoint: http://0.0.0.0:{PORT}/notify/new_order")
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", PORT)), app, log_output=True)
