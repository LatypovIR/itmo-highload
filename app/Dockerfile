FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY orders_service ./orders_service

RUN useradd --system --no-create-home app
USER app

EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=2s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["uvicorn", "orders_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
