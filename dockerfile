FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --upgrade pip  # Фиксит notice о pip 25.3
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN pip install --upgrade pip
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY proxy/ ./proxy/
COPY .env .
EXPOSE $PORT  # Render использует $PORT (env var)
CMD ["sh", "-c", "uvicorn proxy.main:app --host 0.0.0.0 --port $$PORT"]
