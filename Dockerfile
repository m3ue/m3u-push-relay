FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py .

ENV PYTHONPATH=/app
ENV HOST=0.0.0.0

# Render sets $PORT at runtime; uvicorn is started via main.py which reads it
# through pydantic-settings (HOST/PORT env vars), so no fixed EXPOSE is required.
CMD ["python", "main.py"]
