FROM python:3.11-slim-bookworm

# متغيرات لتقليل حجم Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# تثبيت المكتبات الأساسية فقط (بدون برامج غير ضرورية)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    libgl1 \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# تثبيت المكتبات الكبيرة أولاً (لاستفادة من التخزين المؤقت)
COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile -r requirements.txt

# نسخ باقي الملفات
COPY . .

# تقليل حجم طبقة Python (إزالة الملفات غير الضرورية)
RUN find /usr/local/lib/python3.11/site-packages -name "*.pyc" -delete \
    && find /usr/local/lib/python3.11/site-packages -name "__pycache__" -type d -exec rm -rf {} + \
    && rm -rf /root/.cache/pip

CMD ["python", "main.py"]
