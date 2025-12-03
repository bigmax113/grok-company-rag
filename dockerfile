FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --upgrade pip  # Это исправит notice
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN pip install --upgrade pip
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY proxy/ ./proxy/
COPY .env .
EXPOSE 8000
CMD ["uvicorn", "proxy.main:app", "--host", "0.0.0.0", "--port", "8000"]
