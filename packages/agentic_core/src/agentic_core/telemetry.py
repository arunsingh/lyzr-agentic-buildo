"""
Comprehensive OpenTelemetry Instrumentation for AOB Platform
Provides distributed tracing, metrics, and logging across all services
"""

import os
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from functools import wraps
import time
import json

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import Counter, Histogram, Gauge
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.semconv.metrics import MetricInstruments

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AOBTelemetry:
    """Comprehensive telemetry configuration for AOB platform"""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        self.service_name = service_name
        self.service_version = service_version
        self.tracer = None
        self.meter = None
        self.metrics = {}
        self._setup_telemetry()
    
    def _setup_telemetry(self):
        """Initialize OpenTelemetry with comprehensive instrumentation"""
        
        # Resource configuration
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": self.service_version,
            "service.namespace": "aob",
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        })
        
        # Configure OTLP endpoint
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
        
        # Initialize tracer
        trace_provider = TracerProvider(resource=resource)
        trace_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        span_processor = BatchSpanProcessor(trace_exporter)
        trace_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(trace_provider)
        
        self.tracer = trace.get_tracer(self.service_name, self.service_version)
        
        # Initialize metrics
        meter_provider = MeterProvider(resource=resource)
        metric_exporter = OTLPMetricExporter(endpoint=f"{otlp_endpoint}/v1/metrics")
        metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
        meter_provider.add_metric_reader(metric_reader)
        metrics.set_meter_provider(meter_provider)
        
        self.meter = metrics.get_meter(self.service_name, self.service_version)
        
        # Initialize common metrics
        self._setup_metrics()
        
        # Setup instrumentation
        self._setup_instrumentation()
        
        logger.info(f"Telemetry initialized for {self.service_name}")
    
    def _setup_metrics(self):
        """Setup common metrics for the service"""
        
        # Request metrics
        self.metrics["requests_total"] = self.meter.create_counter(
            name="aob_requests_total",
            description="Total number of requests",
            unit="1"
        )
        
        self.metrics["request_duration"] = self.meter.create_histogram(
            name="aob_request_duration_seconds",
            description="Request duration in seconds",
            unit="s"
        )
        
        self.metrics["request_size"] = self.meter.create_histogram(
            name="aob_request_size_bytes",
            description="Request size in bytes",
            unit="By"
        )
        
        self.metrics["response_size"] = self.meter.create_histogram(
            name="aob_response_size_bytes",
            description="Response size in bytes",
            unit="By"
        )
        
        # Workflow metrics
        self.metrics["workflows_total"] = self.meter.create_counter(
            name="aob_workflows_total",
            description="Total number of workflows",
            unit="1"
        )
        
        self.metrics["workflow_duration"] = self.meter.create_histogram(
            name="aob_workflow_duration_seconds",
            description="Workflow execution duration",
            unit="s"
        )
        
        self.metrics["workflow_nodes_total"] = self.meter.create_counter(
            name="aob_workflow_nodes_total",
            description="Total number of workflow nodes executed",
            unit="1"
        )
        
        # Policy metrics
        self.metrics["policy_decisions_total"] = self.meter.create_counter(
            name="aob_policy_decisions_total",
            description="Total number of policy decisions",
            unit="1"
        )
        
        self.metrics["policy_duration"] = self.meter.create_histogram(
            name="aob_policy_duration_seconds",
            description="Policy evaluation duration",
            unit="s"
        )
        
        # Error metrics
        self.metrics["errors_total"] = self.meter.create_counter(
            name="aob_errors_total",
            description="Total number of errors",
            unit="1"
        )
        
        # Resource metrics
        self.metrics["active_connections"] = self.meter.create_gauge(
            name="aob_active_connections",
            description="Number of active connections",
            unit="1"
        )
        
        self.metrics["memory_usage"] = self.meter.create_gauge(
            name="aob_memory_usage_bytes",
            description="Memory usage in bytes",
            unit="By"
        )
    
    def _setup_instrumentation(self):
        """Setup automatic instrumentation for common libraries"""
        
        # Instrument HTTP clients
        HTTPXClientInstrumentor().instrument()
        
        # Instrument databases
        AsyncPGInstrumentor().instrument()
        RedisInstrumentor().instrument()
        
        # Instrument messaging
        KafkaInstrumentor().instrument()
        
        # Instrument logging
        LoggingInstrumentor().instrument()
        
        logger.info("Automatic instrumentation enabled")
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI application"""
        FastAPIInstrumentor.instrument_app(app, tracer_provider=trace.get_tracer_provider())
        logger.info(f"FastAPI instrumentation enabled for {self.service_name}")
    
    @asynccontextmanager
    async def trace_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Context manager for creating spans"""
        span = self.tracer.start_span(name)
        
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            span.end()
    
    def trace_function(self, name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
        """Decorator for tracing functions"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                span_name = name or f"{func.__module__}.{func.__name__}"
                
                with self.tracer.start_as_current_span(span_name) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    
                    # Add function arguments as attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    start_time = time.time()
                    
                    try:
                        if asyncio.iscoroutinefunction(func):
                            result = await func(*args, **kwargs)
                        else:
                            result = func(*args, **kwargs)
                        
                        # Record success metrics
                        duration = time.time() - start_time
                        self.metrics["request_duration"].record(duration)
                        
                        return result
                        
                    except Exception as e:
                        # Record error metrics
                        self.metrics["errors_total"].add(1, {"error_type": type(e).__name__})
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                span_name = name or f"{func.__module__}.{func.__name__}"
                
                with self.tracer.start_as_current_span(span_name) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    start_time = time.time()
                    
                    try:
                        result = func(*args, **kwargs)
                        
                        duration = time.time() - start_time
                        self.metrics["request_duration"].record(duration)
                        
                        return result
                        
                    except Exception as e:
                        self.metrics["errors_total"].add(1, {"error_type": type(e).__name__})
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def record_workflow_metrics(self, workflow_id: str, node_id: str, duration: float, status: str):
        """Record workflow-specific metrics"""
        attributes = {
            "workflow_id": workflow_id,
            "node_id": node_id,
            "status": status,
        }
        
        self.metrics["workflow_nodes_total"].add(1, attributes)
        self.metrics["workflow_duration"].record(duration, attributes)
    
    def record_policy_metrics(self, policy_name: str, decision: bool, duration: float):
        """Record policy-specific metrics"""
        attributes = {
            "policy_name": policy_name,
            "decision": str(decision),
        }
        
        self.metrics["policy_decisions_total"].add(1, attributes)
        self.metrics["policy_duration"].record(duration, attributes)
    
    def record_request_metrics(self, method: str, path: str, status_code: int, duration: float, request_size: int = 0, response_size: int = 0):
        """Record HTTP request metrics"""
        attributes = {
            "method": method,
            "path": path,
            "status_code": str(status_code),
        }
        
        self.metrics["requests_total"].add(1, attributes)
        self.metrics["request_duration"].record(duration, attributes)
        
        if request_size > 0:
            self.metrics["request_size"].record(request_size, attributes)
        
        if response_size > 0:
            self.metrics["response_size"].record(response_size, attributes)
    
    def update_resource_metrics(self, active_connections: int, memory_usage: int):
        """Update resource usage metrics"""
        self.metrics["active_connections"].set(active_connections)
        self.metrics["memory_usage"].set(memory_usage)

# Global telemetry instance
telemetry = AOBTelemetry("aob-platform")

# Convenience functions
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Create a trace span"""
    return telemetry.trace_span(name, attributes)

def trace_function(name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """Trace a function"""
    return telemetry.trace_function(name, attributes)

def record_workflow_metrics(workflow_id: str, node_id: str, duration: float, status: str):
    """Record workflow metrics"""
    telemetry.record_workflow_metrics(workflow_id, node_id, duration, status)

def record_policy_metrics(policy_name: str, decision: bool, duration: float):
    """Record policy metrics"""
    telemetry.record_policy_metrics(policy_name, decision, duration)

def record_request_metrics(method: str, path: str, status_code: int, duration: float, request_size: int = 0, response_size: int = 0):
    """Record request metrics"""
    telemetry.record_request_metrics(method, path, status_code, duration, request_size, response_size)

# FastAPI middleware for automatic request tracing
class TelemetryMiddleware:
    """FastAPI middleware for automatic request tracing and metrics"""
    
    def __init__(self, app):
        self.app = app
        self.telemetry = telemetry
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract request information
        method = scope["method"]
        path = scope["path"]
        
        # Start span
        span_name = f"{method} {path}"
        attributes = {
            SpanAttributes.HTTP_METHOD: method,
            SpanAttributes.HTTP_URL: path,
            SpanAttributes.HTTP_SCHEME: scope.get("scheme", "http"),
            SpanAttributes.HTTP_HOST: scope.get("server", ("", 0))[0],
        }
        
        with self.telemetry.tracer.start_as_current_span(span_name, attributes=attributes) as span:
            start_time = time.time()
            request_size = 0
            response_size = 0
            status_code = 200
            
            # Process request
            try:
                await self.app(scope, receive, send)
            except Exception as e:
                status_code = 500
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
            finally:
                # Record metrics
                duration = time.time() - start_time
                self.telemetry.record_request_metrics(
                    method, path, status_code, duration, request_size, response_size
                )

# Initialize telemetry for the platform
def init_telemetry(service_name: str, service_version: str = "1.0.0") -> AOBTelemetry:
    """Initialize telemetry for a service"""
    return AOBTelemetry(service_name, service_version)
