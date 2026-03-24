FROM python:3.11-slim

WORKDIR /app

# تثبيت Chromium والمكتبات الأساسية فقط
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملف المتطلبات
COPY requirements.txt .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الملفات
COPY . .

CMD ["python", "main.py"]
