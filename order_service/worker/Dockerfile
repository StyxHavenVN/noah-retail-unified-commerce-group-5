FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# tăng độ ổn định khi build
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# log realtime (rất quan trọng khi debug worker)
ENV PYTHONUNBUFFERED=1

CMD ["python", "receive.py"]
