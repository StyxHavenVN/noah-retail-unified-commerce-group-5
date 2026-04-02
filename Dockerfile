# 1. Chọn hệ điều hành nền (Base Image)
# Dùng bản Python 3.9 rút gọn (slim) để nhẹ máy
FROM python:3.9-slim
# 2. Thiết lập thư mục làm việc bên trong Container
WORKDIR /app
# 3. Copy file thư viện vào trước (Tối ưu Cache)
COPY requirements.txt .
# 4. Cài đặt thư viện
RUN pip install --no-cache-dir -r requirements.txt
# 5. Copy toàn bộ code nguồn vào Container
COPY . .
# 6. Khai báo cổng sẽ sử dụng (Optional)
EXPOSE 5000
# 7. Lệnh chạy mặc định khi Container khởi động
CMD ["python", "app.py"]