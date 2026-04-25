🛒 NOAH Retail - Unified Commerce System

Đồ án môn học CMU-CS 445: System Integration Practices.

Dự án xây dựng hệ thống Middleware trung gian nhằm giải quyết tình trạng "Ốc đảo dữ liệu" (Data Silos) cho chuỗi bán lẻ điện tử NOAH Retail, kết nối tự động giữa Kho (Legacy), Bán hàng (MySQL) và Tài chính (PostgreSQL).

👥 Danh sách thành viên & Phân công nhiệm vụ (Nhóm 5)

Giảng viên hướng dẫn: ThS. Võ Đình Hiếu

Đoàn Bảo Khanh (Leader - 29219029482): Module 0 (Hạ tầng Docker) & Module 5 (Kong Security). Giải quyết xung đột mạng Docker và ánh xạ biến môi trường.

Huỳnh Thị Thu An: Module 1 (Legacy Adapter - Đồng bộ kho). Xử lý tự động file CSV và chiến lược Resilience.

Nguyễn Dư Nhật Hào: Module 2 (Order API) & Module 3 (Middleware Worker). Xử lý hàng đợi RabbitMQ và cơ chế Async.

Võ Ngọc Phú: Module 4 (Reporting API). Tích hợp và khâu dữ liệu (Data Stitching) từ đa nguồn.

Nguyễn Minh Nguyên: Module 6 (Dashboard / Frontend). Xây dựng giao diện báo cáo và biểu đồ.

📖 Bối cảnh & Giải pháp Kỹ thuật

NOAH Retail sở hữu 3 hệ thống rời rạc, gây ra tình trạng bán lố hàng (Overselling) và chậm trễ trong xử lý kế toán:

Hệ thống Kho (Legacy AS/400): Chỉ xuất file CSV (inventory.csv).

Hệ thống Bán hàng (Web Store): Lưu trên MySQL.

Hệ thống Tài chính (Finance): Lưu trên PostgreSQL.

👉 Giải pháp: Xây dựng một Middleware dựa trên kiến trúc Microservices để đồng bộ hóa dòng chảy dữ liệu. Dự án áp dụng nguyên tắc Integration Heuristics, đảm bảo các thành phần hoạt động độc lập (Decoupled) thông qua Message Broker và được bảo vệ bởi API Gateway.

📁 Cấu trúc thư mục (Folder Structure)

Để tránh conflict code, mỗi thành viên làm việc trong thư mục tương ứng với module của mình. Tuyệt đối không sửa code trong thư mục của người khác nếu chưa bàn bạc!

noah_retail_project/
├── docker-compose.yml       # File hạ tầng gốc (MySQL, Postgres, RabbitMQ, Kong)
├── init.sql                 # Data mẫu MySQL (20.000 đơn hàng)
├── kong.yml                 # Định tuyến & Security Rules cho API Gateway
├── inventory.csv            # File tồn kho gốc chứa dữ liệu Outliers
│
├── input/                   # Thư mục thả file CSV đầu vào để tự động xử lý
├── processed/               # Thư mục chứa file CSV sau khi đã quét xong
│
├── module1_legacy/          # [Module 1] Code Python quét file CSV kho
│   ├── legacy_adapter.py    # Xử lý Polling & Lọc lỗi OUTLIERS
│   └── requirements.txt
│
├── module2_api/             # [Module 2A] Code API nhận đơn đặt hàng
│   ├── app.py               # Order API (Producer)
│   └── requirements.txt
│
├── module2_worker/          # [Module 2B] Worker xử lý đơn hàng ngầm
│   ├── fix_db.py            # Script hỗ trợ (Vá lỗi cấu trúc DB)
│   ├── worker.py            # Middleware Worker (Consumer) + Tích hợp Telegram Bot
│   └── requirements.txt
│
├── module3_reporting/       # [Module 3] Code API tính toán doanh thu tổng hợp
│   ├── report_api.py        # Data Stitching bằng Pandas
│   └── requirements.txt
│
├── frontend/                # [Module 6] Code HTML UI
│   └── dashboard.html       # Giao diện Báo cáo Thông minh
│
└── README.md                # Tài liệu dự án


🚀 Tính năng & Module Cốt lõi (Core Features)

Module 0: Infrastructure

Container hóa hệ thống bằng Docker Compose với Internal DNS. Cung cấp môi trường thống nhất cho CSDL, Message Queue và Gateway.

Module 1: Legacy Adapter (Đặc thù Nhóm 5)

Auto-polling giám sát liên tục thư mục /input.

Chiến lược xử lý Dữ liệu Bẩn (Dirty Data): Tự động phát hiện lỗi OUTLIERS (Số lượng lớn bất thường, vd: 999999999) bằng block try-except. Đảm bảo hệ thống tiếp tục chạy (Crash-free), ghi nhận vào MySQL và chuyển file sang /processed.

Module 2 & 3: Order Pipeline (Microservices)

Order API: Validate request, lưu sơ bộ (PENDING) vào MySQL và đẩy JSON payload vào RabbitMQ (Cơ chế Fire and Forget).

Order Worker: Lắng nghe hàng đợi order_queue, xử lý độ trễ, ghi giao dịch thành công (SUCCESS) vào PostgreSQL và vòng lại MySQL cập nhật (SYNCED). Xử lý an toàn với ACK message.

🌟 Tính năng mở rộng (Option 1): Tích hợp Notification System tự động gửi tin nhắn Telegram cho khách hàng ngay khi hoàn tất đơn.

Module 4: Data Stitching (Reporting)

Khâu nối dữ liệu (Join) trực tiếp từ MySQL (Web Status) và Postgres (Finance Status) thông qua thư viện Pandas. Hỗ trợ phân trang để xử lý hàng vạn bản ghi mà không tràn RAM.

Module 5: API Gateway (Kong Security)

Bảo vệ toàn bộ kiến trúc bên dưới. Khách hàng/Giao diện chỉ được giao tiếp qua cổng :8000 của Kong với yêu cầu khắt khe:

Key Authentication: Yêu cầu header apikey: noah-secret-key.

Rate Limiting: Chặn spam (tối đa 10 requests/phút).

Module 6: Dashboard

Trung tâm chỉ huy trực quan. Gọi API thông qua Kong Gateway, hiển thị biểu đồ doanh thu và bảng đối soát đơn hàng.

⚙️ Hướng dẫn Khởi chạy (Setup Guide)

1. Khởi động Hạ tầng Core (Docker)

Đảm bảo đã cài đặt Docker Desktop. Mở Terminal tại thư mục gốc:

docker-compose up -d


(Đợi 20s để MySQL nạp dữ liệu từ init.sql và Kong load file cấu hình kong.yml)

2. Cài đặt Môi trường Python (Nên dùng Virtual Environment)

Cài đặt thư viện cho tất cả các modules:

pip install Flask mysql-connector-python psycopg2-binary pika pandas flask-cors requests


3. Khởi chạy các Microservices

Mở 4 cửa sổ Terminal riêng biệt tại thư mục gốc để khởi chạy:

# Terminal 1: Chạy API Nhận đơn hàng
cd module2_api
python app.py

# Terminal 2: Chạy Worker xử lý ngầm
cd module2_worker
python worker.py

# Terminal 3: Chạy API Báo cáo
cd module3_reporting
python report_api.py

# Terminal 4: Chạy Legacy Adapter (Canh chừng thư mục input)
cd module1_legacy
python legacy_adapter.py


🧪 Hướng dẫn Testing (Qua Kong Gateway)

1. Gửi Đơn Hàng Mới

POST http://localhost:8000/api/orders
Headers: 
  - apikey: noah-secret-key
  - Content-Type: application/json

Body:
{
    "user_id": 10,
    "product_id": 101,
    "quantity": 2
}


2. Truy xuất Báo cáo Gộp

GET http://localhost:8000/api/report
Headers: 
  - apikey: noah-secret-key


3. Xem giao diện Dashboard
Mở trực tiếp file frontend/dashboard.html bằng trình duyệt web.

🔮 Hướng phát triển tương lai (Future Works)

Chaos Testing (Thử nghiệm sự cố): Giả lập đánh sập Database hoặc làm chậm Worker để kiểm chứng độ bền vững (Durable) của RabbitMQ và cơ chế tự động kết nối lại (Retry Connection).

Tích hợp Option 2 (Smart Overselling) bằng cách bổ sung Redis cache để kiểm tra tồn kho tốc độ cao trước khi đẩy vào MySQL.

Bản quyền tài liệu thuộc về Nhóm 5 - Lớp CMU-CS 445 NIS (2026).