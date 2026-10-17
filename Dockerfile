# Small official Python image (Debian, without extra tools)
FROM python:3.11-slim

# Don't write .pyc files; send logs straight out (Cloud Run collects them)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Packages first: this layer is reused when only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Only the files the app needs (no tests, no dev tools)
COPY main.py query.py schema.py pipeline.py ./
COPY static ./static

# Run as a normal user, not root
RUN useradd --create-home appuser
USER appuser

# Cloud Run tells the app which port to use in $PORT (8080 by default)
EXPOSE 8080
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
