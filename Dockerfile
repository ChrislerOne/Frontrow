# Playwright's own image: ships Chromium + all OS deps, matched to playwright==1.61.0.
FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY frontend ./frontend

# SQLite lives on a mounted volume so it survives redeploys.
ENV DATABASE_PATH=/data/tracker.db
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

# Single worker: the APScheduler job runs in-process, so >1 worker = duplicate scrapes.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
