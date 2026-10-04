# ---- base image -----------------------------------------------------------
# "slim" = Debian with Python and little else. ~150MB vs ~1GB for the full
# image. Pin the minor version: "python:3" would silently change under you.
FROM python:3.12-slim

# ---- environment ----------------------------------------------------------
# Don't write .pyc files (pointless in a container that gets thrown away)
ENV PYTHONDONTWRITEBYTECODE=1
# Don't buffer stdout — without this, logs appear late or not at all
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ---- dependencies (cached layer) ------------------------------------------
# Copied and installed BEFORE the app code, so editing code doesn't
# invalidate the pip install layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- application code -----------------------------------------------------
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/tickets.csv ./data/tickets.csv
COPY models/classifier.joblib ./models/classifier.joblib

# ---- runtime --------------------------------------------------------------
# Run as a non-root user. If the app is ever compromised, the attacker
# doesn't get root inside the container.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Shell form so $PORT expands — hosting platforms inject their own port.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}