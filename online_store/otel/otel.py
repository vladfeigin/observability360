import logging
from functools import wraps
import atexit
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor



from dotenv import load_dotenv
load_dotenv(override=True)

# Module-level dictionary to avoid duplicate instrumentation configuration
_telemetry_configured_resources = {}


def configure_telemetry(app, service_name: str, service_version: str, deployment_env: str = "demo"):
    
    global _telemetry_configured_resources
    
    if service_name in _telemetry_configured_resources:
        # Return existing instruments if already configured
        return _telemetry_configured_resources[service_name]
    
    # Configure resource with service attributes
    resource = Resource.create(attributes={
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": deployment_env
    })

    # Initialize tracing
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter())
    )
    trace.set_tracer_provider(trace_provider)

    # Initialize metrics
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(OTLPMetricExporter())
        ]
    )
    metrics.set_meter_provider(meter_provider)
    
    # Configure logging
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    log_exporter = OTLPLogExporter(insecure=True)
    log_processor = BatchLogRecordProcessor(log_exporter)
    logger_provider.add_log_record_processor(log_processor)

    logging_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().addHandler(logging_handler)
    
    # Auto-instrumentation
    if app:
        FastAPIInstrumentor.instrument_app(app)
    SQLite3Instrumentor().instrument()
    RequestsInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=True)

    # Use a combined name for meter and tracer instead of __name__
    identifier = f"{service_name}-{service_version}"
    
    _telemetry_configured_resources[service_name] = {
        "meter": metrics.get_meter(identifier),
        "tracer": trace.get_tracer(identifier),
        "logger": logging.getLogger(identifier)
    }
    
    return _telemetry_configured_resources[service_name]


def trace_span(span_name, tracer):
    """A decorator to trace function execution with a span."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("function.name", func.__name__)
                return func(*args, **kwargs)
        return wrapper
    return decorator

def shutdown_telemetry():
    trace.get_tracer_provider().shutdown()
    metrics.get_meter_provider().shutdown()
    logging.getLogger().handlers.clear()

atexit.register(shutdown_telemetry)
