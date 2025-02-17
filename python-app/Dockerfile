
FROM python:3.11-slim
WORKDIR /app

# Copy entire folder contents
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["uvicorn", "main_service:app", "--host", "0.0.0.0", "--port", "8000"]