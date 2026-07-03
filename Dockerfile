FROM python:3.11-slim

WORKDIR /code

# نسخ ملف المتطلبات وتثبيتها في البيئة الحالية
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# إنشاء مجلد باسم app داخل السيرفر ليتوافق مع استدعاءات الكود الخاصة بك
RUN mkdir -p /code/app

# نسخ الملفات البرمجية الأساسية إلى داخل مجلد app الجديد
COPY ./main.py /code/app/main.py
COPY ./database.py /code/app/database.py

# نسخ بقية الملفات إلى المجلد الرئيسي
COPY . /code/

EXPOSE 8000

# تشغيل التطبيق بالإشارة إلى المجلد الجديد
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
