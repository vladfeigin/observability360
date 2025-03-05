# otel.py - Dedicated instrumentation module
from functools import wraps
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

from dotenv import load_dotenv
load_dotenv(override=True)

# Module-level flag to avoid duplicate configuration
_telemetry_configured = False

def configure_telemetry(app, service_name: str, service_version: str, deployment_env: str = "demo"):
    global _telemetry_configured
    if _telemetry_configured:
        # Return existing instruments if already configured
        return {
            "meter": metrics.get_meter(__name__),
            "tracer": trace.get_tracer(__name__)
        }

    # Configure resource
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

    # Auto-instrumentation
    if app:
        FastAPIInstrumentor.instrument_app(app)
    SQLite3Instrumentor().instrument()
    RequestsInstrumentor().instrument()

    _telemetry_configured = True

    # Return instruments for manual instrumentation
    return {
        "meter": metrics.get_meter(__name__),
        "tracer": trace.get_tracer(__name__)
    }
    
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