"""
Observability and monitoring setup for the voice authentication microservice.
"""

import time
from typing import Optional, Dict, Any, Callable
from functools import wraps

import structlog
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

logger = structlog.get_logger()

# Global tracer and meter
tracer: Optional[trace.Tracer] = None
meter: Optional[metrics.Meter] = None

# Metrics instruments
request_counter: Optional[metrics.Counter] = None
request_duration: Optional[metrics.Histogram] = None
error_counter: Optional[metrics.Counter] = None
enrollment_counter: Optional[metrics.Counter] = None
verification_counter: Optional[metrics.Counter] = None
verification_score_histogram: Optional[metrics.Histogram] = None


def setup_observability(
    service_name: str = "voice-auth-microservice",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = True
) -> None:
    """
    Set up OpenTelemetry tracing and metrics.
    
    Args:
        service_name: Name of the service for tracing
        service_version: Version of the service
        otlp_endpoint: OTLP endpoint for trace/metric export
        enable_console_export: Whether to enable console export for development
    """
    global tracer, meter
    global request_counter, request_duration, error_counter
    global enrollment_counter, verification_counter, verification_score_histogram
    
    logger.info(
        "Setting up observability",
        service_name=service_name,
        service_version=service_version,
        otlp_endpoint=otlp_endpoint
    )
    
    # Set up tracing
    trace_provider = TracerProvider(
        resource=trace.Resource.create({
            "service.name": service_name,
            "service.version": service_version,
        })
    )
    
    # Add span processors
    if otlp_endpoint:
        otlp_span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        trace_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))
    
    if enable_console_export:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        console_span_exporter = ConsoleSpanExporter()
        trace_provider.add_span_processor(BatchSpanProcessor(console_span_exporter))
    
    trace.set_tracer_provider(trace_provider)
    tracer = trace.get_tracer(__name__)
    
    # Set up metrics
    metric_readers = []
    
    if otlp_endpoint:
        otlp_metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
        metric_readers.append(
            PeriodicExportingMetricReader(
                exporter=otlp_metric_exporter,
                export_interval_millis=30000  # 30 seconds
            )
        )
    
    if enable_console_export:
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
        console_metric_exporter = ConsoleMetricExporter()
        metric_readers.append(
            PeriodicExportingMetricReader(
                exporter=console_metric_exporter,
                export_interval_millis=60000  # 60 seconds
            )
        )
    
    meter_provider = MeterProvider(
        resource=metrics.Resource.create({
            "service.name": service_name,
            "service.version": service_version,
        }),
        metric_readers=metric_readers
    )
    
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter(__name__)
    
    # Create metric instruments
    request_counter = meter.create_counter(
        name="http_requests_total",
        description="Total number of HTTP requests",
        unit="1"
    )
    
    request_duration = meter.create_histogram(
        name="http_request_duration_seconds",
        description="HTTP request duration in seconds",
        unit="s"
    )
    
    error_counter = meter.create_counter(
        name="http_errors_total",
        description="Total number of HTTP errors",
        unit="1"
    )
    
    enrollment_counter = meter.create_counter(
        name="voice_enrollments_total",
        description="Total number of voice enrollments",
        unit="1"
    )
    
    verification_counter = meter.create_counter(
        name="voice_verifications_total",
        description="Total number of voice verifications",
        unit="1"
    )
    
    verification_score_histogram = meter.create_histogram(
        name="voice_verification_score",
        description="Voice verification similarity scores",
        unit="1"
    )
    
    logger.info("Observability setup completed")


def instrument_fastapi_app(app) -> None:
    """
    Instrument FastAPI application with OpenTelemetry.
    
    Args:
        app: FastAPI application instance
    """
    if tracer is None:
        logger.warning("Tracer not initialized, call setup_observability() first")
        return
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument HTTP client
    HTTPXClientInstrumentor().instrument()
    
    # Instrument logging
    LoggingInstrumentor().instrument(set_logging_format=True)
    
    logger.info("FastAPI application instrumented with OpenTelemetry")


def trace_function(operation_name: Optional[str] = None):
    """
    Decorator to trace function execution.
    
    Args:
        operation_name: Optional custom operation name for the span
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if tracer is None:
                return await func(*args, **kwargs)
            
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add function metadata to span
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Mark span as successful
                    span.set_attribute("success", True)
                    
                    return result
                    
                except Exception as e:
                    # Record exception in span
                    span.record_exception(e)
                    span.set_attribute("success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    
                    raise e
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if tracer is None:
                return func(*args, **kwargs)
            
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add function metadata to span
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Mark span as successful
                    span.set_attribute("success", True)
                    
                    return result
                    
                except Exception as e:
                    # Record exception in span
                    span.record_exception(e)
                    span.set_attribute("success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    
                    raise e
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def record_enrollment_metrics(success: bool, processing_time: float, user_id: str) -> None:
    """
    Record metrics for enrollment operations.
    
    Args:
        success: Whether enrollment was successful
        processing_time: Time taken for enrollment in seconds
        user_id: User ID for attribution
    """
    if enrollment_counter is None or request_duration is None:
        return
    
    attributes = {
        "operation": "enrollment",
        "success": str(success).lower(),
        "user_id": user_id
    }
    
    enrollment_counter.add(1, attributes)
    request_duration.record(processing_time, attributes)
    
    logger.info(
        "Enrollment metrics recorded",
        success=success,
        processing_time=processing_time,
        user_id=user_id
    )


def record_verification_metrics(
    success: bool,
    processing_time: float,
    similarity_score: Optional[float],
    user_id: str
) -> None:
    """
    Record metrics for verification operations.
    
    Args:
        success: Whether verification was successful
        processing_time: Time taken for verification in seconds
        similarity_score: Voice similarity score (if available)
        user_id: User ID for attribution
    """
    if verification_counter is None or request_duration is None:
        return
    
    attributes = {
        "operation": "verification",
        "success": str(success).lower(),
        "user_id": user_id
    }
    
    verification_counter.add(1, attributes)
    request_duration.record(processing_time, attributes)
    
    # Record similarity score if available
    if similarity_score is not None and verification_score_histogram is not None:
        score_attributes = {
            "success": str(success).lower(),
            "user_id": user_id
        }
        verification_score_histogram.record(similarity_score, score_attributes)
    
    logger.info(
        "Verification metrics recorded",
        success=success,
        processing_time=processing_time,
        similarity_score=similarity_score,
        user_id=user_id
    )


def record_http_metrics(
    method: str,
    path: str,
    status_code: int,
    processing_time: float
) -> None:
    """
    Record HTTP request metrics.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        processing_time: Request processing time in seconds
    """
    if request_counter is None or request_duration is None or error_counter is None:
        return
    
    attributes = {
        "method": method,
        "path": path,
        "status_code": str(status_code)
    }
    
    request_counter.add(1, attributes)
    request_duration.record(processing_time, attributes)
    
    # Record errors
    if status_code >= 400:
        error_attributes = {
            "method": method,
            "path": path,
            "status_code": str(status_code),
            "error_type": "client_error" if status_code < 500 else "server_error"
        }
        error_counter.add(1, error_attributes)


def get_trace_context() -> Dict[str, Any]:
    """
    Get current trace context information.
    
    Returns:
        Dict with trace ID and span ID if available
    """
    current_span = trace.get_current_span()
    if current_span is None or not current_span.is_recording():
        return {}
    
    span_context = current_span.get_span_context()
    return {
        "trace_id": f"{span_context.trace_id:032x}",
        "span_id": f"{span_context.span_id:016x}",
        "trace_flags": span_context.trace_flags
    }


class TracingContextMiddleware:
    """
    Middleware to add tracing context to structured logs.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Add trace context to structured logging
        trace_context = get_trace_context()
        if trace_context:
            structlog.contextvars.bind_contextvars(**trace_context)
        
        await self.app(scope, receive, send)