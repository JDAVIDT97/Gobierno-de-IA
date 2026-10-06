FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 USE_TF=0
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m api.model_bundle
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import requests; requests.get('http://127.0.0.1:8000/health', timeout=3).raise_for_status()"
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
