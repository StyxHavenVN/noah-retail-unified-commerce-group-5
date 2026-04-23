# Base image nhẹ, ổn định
FROM python:3.10-slim

WORKDIR /app

# Cài dependencies trước (tối ưu cache)
COPY requirements.txt .

# cải thiện độ ổn định khi build
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# đảm bảo log in ra ngay (không bị buffer)
ENV PYTHONUNBUFFERED=1

# Expose port Flask
EXPOSE 5000

# Chạy app
CMD ["python", "app.py"]
