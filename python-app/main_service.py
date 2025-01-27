
# main.py - Clean application code
import logging
import time
import random
from dotenv import load_dotenv
from fastapi import FastAPI
from opentelemetry.trace import Status, StatusCode
from otel import configure_telemetry

load_dotenv(override=True)

app = FastAPI()
instruments = configure_telemetry(app)

# Get instruments
meter = instruments["meter"]
tracer = instruments["tracer"]

# Create metrics instruments
request_counter = meter.create_counter(
    name="http_requests_total",
    description="Total number of HTTP requests",
    unit="1"
)

@app.get("/process")
async def process_request():
    # Start auto-created span from FastAPI instrumentation
    with tracer.start_as_current_span("process_request") as span:
        # Simulate work
        start_time = time.time()
        time.sleep(random.uniform(0.1, 0.5))
        
        try:
            request_counter.add(1, attributes={"route": "/process"})
            internal_function_1()
            
            logging.info("Request processed successfully")
            return {"status": "success"}
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            logging.error("Request processing failed")
            return {"status": "error"}

def internal_function_1():
    with tracer.start_as_current_span("internal_function"):
        # Simulate work
        random_string = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
        logging.info(f"Generated string: {random_string}")
        return random_string

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)