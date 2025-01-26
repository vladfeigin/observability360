

# main.py
import logging
import time
import random
from fastapi import FastAPI
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.metrics._internal.aggregation import Observation 

# Configure resource
resource = Resource.create({
    "service.name": "python-backend-service",
    "service.version": "1.1.0",
    "deployment.environment": "demo",
    "agent_name": "null"
})

# Initialize tracing
trace_provider = TracerProvider(resource=resource)
trace_processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
)
trace_provider.add_span_processor(trace_processor)
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)


# Initialize metrics
metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# Create metrics instruments
request_counter = meter.create_counter(
    name="http_requests_total",
    description="Total number of HTTP requests",
    unit="1"
)

response_time_histogram = meter.create_histogram(
    name="http_response_time_seconds",
    description="HTTP response times",
    unit="s"
)


# Initialize logging
logger_provider = LoggerProvider(resource=resource)
set_logger_provider(logger_provider)
log_exporter = OTLPLogExporter(endpoint="http://otel-collector:4317", insecure=True)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
handler = LoggingHandler(logger_provider=logger_provider)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

app = FastAPI()

@app.get("/process")
async def process_request():
    # Start a span
    with tracer.start_as_current_span("process_request_func") as span:
        # Add span attributes
        span.set_attributes({
            "http.method": "GET",
            "http.route": "/process",
            "request.id": str(random.randint(1000, 9999))
        })
        
        # Simulate work
        start_time = time.time()
        time.sleep(random.uniform(0.1, 0.5))
        
        try:
            # Record metrics
            request_counter.add(1)
            duration = time.time() - start_time
            response_time_histogram.record(duration)
            
            rs = internal_function_1()

            # Log message
            logging.info("Request processed successfully. open telemetry test", extra={
                "duration": duration,
                "status": "success"
            })
            
            return {"status": "success", "duration": duration}
            
        except Exception as e:
            # Record error
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            logging.error("Request processing failed", exc_info=True)
            return {"status": "error"}
        
        
def internal_function_1():
    logging.info("internal_function_1...")
    
    with tracer.start_as_current_span("internal_function") as span:
        span.set_attribute("function", "internal_function")
        #create random string to simulate work
        random_string = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
        
        logging.info(f"internal_function_1: random string generated: {random_string}") 
        return random_string       

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

