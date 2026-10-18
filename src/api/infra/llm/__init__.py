"""LLM calls: declare an ``LlmTask``, call ``run_llm``; every call lands in the active capture.

Usable from the domain layer (no database here). Persistence is the app layer's job:
``api.app.llm_calls.llm_journal`` opens the capture and writes the journal tables.
"""

from api.infra.llm.capture import capture_llm_calls, record_llm_call
from api.infra.llm.config import MODEL_PRICING, LlmCall
from api.infra.llm.record import LlmCallRecord, LlmRetry, LlmUsage, estimate_cost, prompt_hash
from api.infra.llm.run import run_llm
from api.infra.llm.task import LlmTask, Tier, agent_for, get_model

__all__ = [
    "MODEL_PRICING",
    "LlmCall",
    "LlmCallRecord",
    "LlmRetry",
    "LlmTask",
    "LlmUsage",
    "Tier",
    "agent_for",
    "capture_llm_calls",
    "estimate_cost",
    "get_model",
    "prompt_hash",
    "record_llm_call",
    "run_llm",
]
