# NOAH Retail - Unified Commerce System

Đồ án môn học **CMU-CS 445 System Integration Practices**

Dự án xây dựng hệ thống Middleware trung gian nhằm giải quyết tình trạng "Ốc đảo dữ liệu" (Data Silos) cho chuỗi bán lẻ điện tử NOAH Retail, kết nối tự động giữa Kho (Legacy), Bán hàng (MySQL) và Tài chính (PostgreSQL).

---

## Danh sách thành viên & Phân công nhiệm vụ

* **Đoàn Bảo Khanh (Leader):** Module 0 (Hạ tầng Docker) & Module 5 (Kong Security).
* **Huỳnh Thị Thu An:** Module 1 (Legacy Adapter - Đồng bộ kho).
* **Nguyễn Dư Nhật Hào:** Module 2 (Order API) & Module 3 (Middleware Worker).
* **Võ Ngọc Phú:** Module 4 (Reporting API).
* **Nguyễn Minh Nguyên:** Module 6 (Dashboard / Frontend).

---

## Cấu trúc thư mục (Folder Structure)

Để tránh conflict code, mỗi người sẽ làm việc trong thư mục (folder) tương ứng với module của mình. Tuyệt đối không sửa code trong thư mục của người khác nếu chưa bàn bạc!

```text
noah-retail-unified-commerce/
├── docker-compose.yml       # File hạ tầng gốc 
├── kong_config/             # File cấu hình Kong Gateway
│   └── kong.yml             
├── legacy_adapter/          # Code Python quét file CSV kho
│   ├── input/               # Thư mục thả file CSV đầu vào
│   ├── processed/           # Thư mục chứa file CSV đã xử lý xong
│   └── app.py               
├── order_service/           # Code API nhận đơn và Worker RabbitMQ
├── report_service/          # Code API tính toán doanh thu tổng hợp
├── dashboard/               # Code Streamlit/Web UI
└── README.md                
