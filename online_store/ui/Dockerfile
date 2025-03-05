FROM python:3.9-slim

WORKDIR /online_store

COPY ui/requirements.txt requirements.txt

RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY ui ui
COPY otel otel

# Expose the port that Streamlit will run on
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "ui/online_store_ui.py"]