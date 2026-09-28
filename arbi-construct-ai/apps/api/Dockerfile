FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/ .
COPY scripts/ /app/scripts/

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && (python /app/scripts/seed/run_all_seeds.py || echo 'Seeding failed (non-fatal), continuing...') && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
