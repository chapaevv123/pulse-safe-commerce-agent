FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
ENV PORT=8000 PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com DATABASE_PATH=/tmp/safe_commerce.db
CMD ["sh", "-c", "uvicorn pulse_safe_commerce_agent.app:app --host 0.0.0.0 --port ${PORT}"]
