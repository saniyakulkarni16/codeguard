FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY codeguard ./codeguard
COPY samples ./samples
EXPOSE 8000
CMD ["uvicorn", "codeguard.api:app", "--host", "0.0.0.0", "--port", "8000"]
