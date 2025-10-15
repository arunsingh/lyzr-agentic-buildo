from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator, Optional

try:
    from opentelemetry import trace
    from opentelemetry.trace import Tracer
except Exception:  # pragma: no cover
    trace = None  # type: ignore
    Tracer = None  # type: ignore


def init(exporter: Optional[str] = None) -> None:
    if trace is None:
        return
    # Minimal init; users can configure env OTEL_EXPORTER_OTLP_ENDPOINT
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "agentic-core"}))
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


@contextmanager
def span(name: str) -> Iterator[None]:
    if trace is None:
        yield
        return
    tracer = trace.get_tracer("agentic_core")
    with tracer.start_as_current_span(name):
        yield

