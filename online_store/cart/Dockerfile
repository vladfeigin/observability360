FROM python:3.9-slim

WORKDIR /app

RUN mkdir online_store
WORKDIR /app/online_store

COPY cart/requirements.txt requirements.txt

RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY cart cart
COPY otel otel

# Expose the port that Streamlit will run on
EXPOSE 5002

WORKDIR /app

CMD ["python", "-m", "online_store.cart.app"]