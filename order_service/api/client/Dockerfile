FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# thêm --upgrade pip để tránh lỗi lib
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# đảm bảo log hiện ngay (không bị buffer)
ENV PYTHONUNBUFFERED=1

CMD ["python", "test_api.py"]
