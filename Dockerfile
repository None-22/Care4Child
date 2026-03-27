# ============================================================
# Dockerfile — Care4Child Django Application
# ============================================================

# استخدام Python 3.12 slim كصورة أساسية خفيفة
FROM python:3.12-slim

# منع Python من كتابة ملفات .pyc وتفعيل stdout/stderr بدون بافر
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# تثبيت المتطلبات أولاً (لاستخدام طبقات Docker المؤقتة cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ بقية ملفات المشروع
COPY . .

# جمع الملفات الثابتة
RUN python manage.py collectstatic --no-input

# فتح المنفذ 8000
EXPOSE 8000

# أمر التشغيل الافتراضي باستخدام Gunicorn
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
