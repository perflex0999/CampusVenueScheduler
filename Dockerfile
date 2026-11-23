FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000

CMD ["python", "-m", "scripts.run_server"]
