FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    "uvicorn[standard]==0.32.0" \
    prometheus-client==0.21.0 \
    prometheus-fastapi-instrumentator==7.0.0 \
    psycopg2-binary==2.9.10

COPY app ./app

ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]