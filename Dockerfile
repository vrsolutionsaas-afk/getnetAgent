FROM python:3.11-slim

# Evita .pyc e mantem logs sem buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias de sistema minimas (psycopg/lxml)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Shell form para expandir ${PORT} (Railway injeta a porta em runtime; local usa 8000)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
