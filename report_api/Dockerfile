FROM python:3.9-slim

WORKDIR /app

# Cài thư viện (pandas + sqlalchemy, thêm Flask + drivers)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code
COPY . .

# Expose port 5001 (khớp với kong.yml: http://report-api:5001)
EXPOSE 5001

CMD ["python", "report_api.py"]
