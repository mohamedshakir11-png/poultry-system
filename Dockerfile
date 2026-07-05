FROM python:3.11-slim

WORKDIR /code

# تحميل المكتبات أولاً
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# نسخ كافة الملفات مباشرة في المجلد الرئيسي دون تفريع
COPY . /code/

# فتح المنفذ الخاص بـ Hugging Face
EXPOSE 7860

# أمر التشغيل المباشر لملف main.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
