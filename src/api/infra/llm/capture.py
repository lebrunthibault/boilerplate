"""Per-run capture of LLM calls via ContextVar — the app layer opens it and persists the list.

Active only inside a capture, a no-op elsewhere (scripts, unit tests): a call made outside
``capture_llm_calls`` is logged on stdlib logging only. This split lets the domain layer call an
LLM without ever touching the database (cf. the ``domain-stateless`` import contract).
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

from api.infra.llm.record import LlmCallRecord

_calls: ContextVar[list[LlmCallRecord] | None] = ContextVar("_llm_calls", default=None)


@contextmanager
def capture_llm_calls() -> Generator[list[LlmCallRecord], None, None]:
    """Collect every LLM call issued in this context (same asyncio task and its children)."""
    calls: list[LlmCallRecord] = []
    token = _calls.set(calls)
    try:
        yield calls
    finally:
        _calls.reset(token)


def record_llm_call(record: LlmCallRecord) -> None:
    """Append one call to the active capture; no-op outside a capture."""
    calls = _calls.get(None)
    if calls is None:
        return
    calls.append(record)
