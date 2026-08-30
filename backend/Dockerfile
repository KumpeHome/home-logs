FROM python:3.14.6-slim-trixie

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 1000 appuser
COPY pyproject.toml /app/pyproject.toml
COPY app /app/app
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir . \
    && mkdir -p /data/uploads \
    && chmod +x /app/docker-entrypoint.sh \
    && chown appuser:appuser /data/uploads

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
