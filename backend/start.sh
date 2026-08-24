#!/bin/sh
cd /app
# Run database migrations (if alembic is available)
if [ -f "alembic.ini" ]; then
    python -m alembic upgrade head
fi
# Start the application
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}