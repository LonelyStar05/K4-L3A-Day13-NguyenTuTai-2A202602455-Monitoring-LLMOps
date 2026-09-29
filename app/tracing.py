from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

try:
    from langfuse import get_client, observe, propagate_attributes

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyClient:
        def update_current_span(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

    def get_client():
        return _DummyClient()

    @contextmanager
    def propagate_attributes(**kwargs: Any):
        yield


def get_langfuse_client():
    return get_client()

@contextmanager
def start_child_observation(*, client: Any, name: str, as_type: str, **kwargs: Any):
    """Start a Langfuse v4 child observation when the client supports it.

    Falls back to a no-op context manager when tracing is disabled or the
    client is a lightweight stub (e.g. in unit tests), so the agent logic
    remains exactly the same with and without Langfuse.
    """
    if not tracing_enabled():
        yield None
        return
    starter = getattr(client, "start_as_current_observation", None)
    if not callable(starter):
        yield None
        return
    with starter(name=name, as_type=as_type, **kwargs) as child:
        yield child


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )
