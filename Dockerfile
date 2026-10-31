FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY frontend ./frontend
RUN useradd -m auditor && mkdir -p /app/data && chown auditor:auditor /app/data
USER auditor
EXPOSE 8000
CMD ["uvicorn","backend.main:app","--host","0.0.0.0","--port","8000","--workers","1"]
