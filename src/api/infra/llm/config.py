"""LLM call guardrails and pricing — one place for every value (cf. docs/coding-style.md)."""

from __future__ import annotations


class LlmCall:
    """Transport guardrails shared by every LLM task.

    TIMEOUT_S bounds a hung provider; a task with a known slower profile overrides it through
    ``LlmTask.timeout_s``. MAX_OUTPUT_TOKENS bounds a degenerate generation — beware that
    structured output goes through tool-calling, so a reached cap truncates the tool arguments
    and fails the call rather than returning a partial answer. TEMPERATURE 0 keeps runs
    reproducible. INPUT_LOG_CHARS caps the input copied into the journal (the model still
    receives the full text).
    """

    TIMEOUT_S = 30.0
    MAX_OUTPUT_TOKENS = 1024
    TEMPERATURE = 0.0
    INPUT_LOG_CHARS = 20_000


# Price per token in USD, (input, output), keyed by the exact model string of LLM_MODEL_*.
# Example: "mistral:mistral-small-latest": (0.15e-6, 0.6e-6) for $0.15 / $0.60 per 1M tokens.
# A model missing here is journaled with cost_usd = None (unknown), never 0.
MODEL_PRICING: dict[str, tuple[float, float]] = {}
