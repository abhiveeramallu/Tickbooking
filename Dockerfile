FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/alembic.ini .
COPY backend/migrations ./migrations
COPY backend/start.sh .
RUN chmod +x start.sh

EXPOSE 8000

CMD ["sh", "start.sh"]