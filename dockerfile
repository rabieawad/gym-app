# base image
FROM python:3.11-slim

# python: unbuffered logs (show up in `docker logs`), no .pyc files in the image
# app: production mode + database location (the /data volume, see below)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ENVIRONMENT=production \
    DATABASE_URL=sqlite:////data/gym.db

# set working dir
WORKDIR /app

# install packages (own layer: cached until requirements.txt changes)
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# copy the app to the image
COPY backend/app ./backend/app
COPY frontend ./frontend

# run as a non-root user; /data is where the SQLite file lives
RUN useradd --system --uid 10001 --no-create-home appuser \
    && mkdir /data \
    && chown appuser:appuser /data
USER appuser

# uvicorn must start from the folder that contains the `app` package
WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]