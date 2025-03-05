FROM python:3.9-slim

WORKDIR /app

RUN mkdir online_store
WORKDIR /app/online_store

COPY product/requirements.txt requirements.txt

RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY product product
COPY otel otel

# Expose the port that Streamlit will run on
EXPOSE 5001

WORKDIR /app

CMD ["python", "-m", "online_store.product.app"]