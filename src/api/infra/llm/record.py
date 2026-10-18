"""What the journal keeps of one LLM call, and the helpers that read it off a pydantic-ai run."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic_ai.messages import ModelRequest, RetryPromptPart

from api.infra.llm.config import MODEL_PRICING

# Size cap of a retry error rendered back to the model.
_RETRY_ERROR_CHARS = 2000


@dataclass(frozen=True)
class LlmUsage:
    """Tokens consumed by one call (all requests of the run, retries included)."""

    input_tokens: int
    output_tokens: int
    requests: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class LlmRetry:
    """A validation error sent back to the model during the run (RetryPromptPart)."""

    tool: str | None
    error: str


@dataclass(frozen=True)
class LlmCallRecord:
    """One LLM call, success or failure, as the app layer persists it in ``llm_call``.

    ``system_prompt`` travels in memory only: the journal stores it once in ``llm_prompt``
    and references it by ``prompt_hash``.
    """

    task: str
    model: str
    system_prompt: str
    input: str
    output: Any
    usage: LlmUsage | None
    duration_ms: int
    created_at: datetime
    error: str | None = None
    retries: list[LlmRetry] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def prompt_hash(self) -> str:
        return prompt_hash(self.system_prompt)

    @property
    def cost_usd(self) -> float | None:
        return estimate_cost(self.model, self.usage)


def prompt_hash(text: str) -> str:
    """sha256 (hex) of a system prompt — dedup key of the ``llm_prompt`` table."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def estimate_cost(model: str, usage: LlmUsage | None) -> float | None:
    """USD cost from MODEL_PRICING; None when the model is not priced or usage is unknown."""
    price = MODEL_PRICING.get(model)
    if price is None or usage is None:
        return None
    in_price, out_price = price
    return round(usage.input_tokens * in_price + usage.output_tokens * out_price, 6)


def llm_usage(result: Any) -> LlmUsage | None:
    """Best-effort token count of a pydantic-ai run result."""
    usage = getattr(result, "usage", None)
    if usage is None:
        return None
    return LlmUsage(
        input_tokens=usage.input_tokens or 0,
        output_tokens=usage.output_tokens or 0,
        requests=usage.requests or 0,
    )


def llm_retries(result: Any) -> list[LlmRetry]:
    """Validation errors rendered back to the model during the run (empty in the nominal case)."""
    try:
        messages = result.all_messages()
    except Exception:
        return []
    return [
        LlmRetry(tool=part.tool_name, error=part.model_response()[:_RETRY_ERROR_CHARS])
        for msg in messages
        if isinstance(msg, ModelRequest)
        for part in msg.parts
        if isinstance(part, RetryPromptPart)
    ]


def output_json(output: Any) -> Any:
    """JSON-ready form of a task output (pydantic model dumped, text kept as is)."""
    if isinstance(output, BaseModel):
        return output.model_dump(mode="json")
    return output
