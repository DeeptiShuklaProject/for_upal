FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    FORWARDED_ALLOW_IPS=127.0.0.1

WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock \
    && useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser main.py index.html ./
COPY --chown=appuser:appuser professor_qa ./professor_qa
COPY --chown=appuser:appuser data ./data
COPY --chown=appuser:appuser static ./static

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/api/health', timeout=3)" || exit 1

CMD ["sh", "-c", "exec python -m uvicorn main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips ${FORWARDED_ALLOW_IPS:-127.0.0.1}"]
