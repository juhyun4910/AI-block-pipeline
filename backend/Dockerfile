FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend /app/backend
COPY backend/app.py /app/backend_app.py
ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
