FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# OCR language packs match TESSERACT_LANGS in .env.example. poppler-utils
# renders scanned PDF pages.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-rus \
        tesseract-ocr-uzb \
        tesseract-ocr-uzb-cyrl \
        tesseract-ocr-eng \
        poppler-utils \
        libmagic1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the source the editable install + migrations need BEFORE pip install,
# so setuptools finds the `app` package and Alembic finds its scripts.
COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY docker-entrypoint.sh ./docker-entrypoint.sh

RUN pip install --upgrade pip && pip install -e . \
    && chmod +x docker-entrypoint.sh

EXPOSE 8000

# Entrypoint runs `alembic upgrade head`, seeds the admin (idempotent),
# then execs uvicorn.
ENTRYPOINT ["./docker-entrypoint.sh"]
