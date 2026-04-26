# 🚀 Hướng Dẫn Chạy Project - NOAH Retail Unified Commerce

## 📋 Yêu cầu cài đặt

- **Docker Desktop** (bắt buộc)
- **Git** (để clone repo)

## ⚡ Chạy Project (1 lệnh duy nhất)

```bash
# Mở terminal tại thư mục gốc project
docker-compose up -d --build
```

> Đợi **~30 giây** để MySQL nạp dữ liệu và các service khởi động hoàn tất.

## 🔗 Truy cập các dịch vụ

### Mở trên trình duyệt:

| Dịch vụ | URL | Ghi chú |
|---------|-----|---------|
| **Dashboard** | http://localhost:8501 | Giao diện chính |
| **RabbitMQ UI** | http://localhost:15672 | Login: `user` / `password` |

### API (dùng `curl` hoặc Postman — **KHÔNG mở trên trình duyệt**):

| API | Endpoint | Header bắt buộc |
|-----|----------|-----------------|
| **Order API** | `http://localhost:8000/api/orders` | `apikey: noah-secret-key` |
| **Report API** | `http://localhost:8000/api/report` | `apikey: noah-secret-key` |

### Database (kết nối bằng tool như DBeaver, DataGrip):

| DB | Host | User / Password |
|----|------|-----------------|
| **MySQL** | `localhost:3307` | `root` / `rootpassword` |
| **PostgreSQL** | `localhost:5432` | `finance_user` / `finance_password` |

> ⚠️ Mở `http://localhost:8000` trên trình duyệt sẽ báo lỗi — đây là **bình thường**. Kong là API Gateway, chỉ hoạt động khi gọi đúng route + kèm header `apikey`.

## 🧪 Test nhanh qua Kong Gateway

**Tạo đơn hàng:**
```bash
curl -X POST http://localhost:8000/api/orders \
  -H "apikey: noah-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 10, "product_id": 101, "quantity": 2}'
```

**Xem báo cáo:**
```bash
curl http://localhost:8000/api/report -H "apikey: noah-secret-key"
```

## 🛑 Dừng Project

```bash
docker-compose down          # Dừng (giữ data)
docker-compose down -v       # Dừng + xóa toàn bộ data
```

## 🔧 Xử lý lỗi thường gặp

| Lỗi | Cách khắc phục |
|-----|----------------|
| Port bị chiếm | `docker-compose down` rồi chạy lại |
| MySQL chưa sẵn sàng | Đợi thêm 30s hoặc `docker logs noah_mysql` |
| Build lỗi | `docker-compose build --no-cache` rồi `up -d` |
| Xem log service | `docker logs <tên_container>` (vd: `docker logs order_api`) |

## 📦 Danh sách 9 Container

1. `noah_mysql` — MySQL 8.0 (Web Store DB)
2. `noah_postgres` — PostgreSQL 15 (Finance DB)
3. `noah_rabbitmq` — RabbitMQ (Message Broker)
4. `order_api` — Order API (Flask, port 5000)
5. `order_worker` — Order Worker (Consumer RabbitMQ)
6. `report_api` — Report API - Data Stitching (port 5001)
7. `noah_dashboard` — Streamlit Dashboard (port 8501)
8. `kong_gateway` — Kong API Gateway (port 8000)
9. `legacy_adapter` — Legacy CSV Adapter

---
*Nhóm 5 - CMU-CS 445 NIS (2026)*
