# Hugging Face Space (SDK: docker) - app Plotly Dash
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
RUN adduser --disabled-password --gecos "" appuser
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 7860
ENV PORT=7860
ENV WEB_CONCURRENCY=1
ENV GUNICORN_TIMEOUT=120
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT', '7860'), timeout=3).read()" || exit 1
CMD ["sh", "-c", "gunicorn app:server --bind 0.0.0.0:${PORT:-7860} --workers ${WEB_CONCURRENCY:-1} --timeout ${GUNICORN_TIMEOUT:-120}"]
