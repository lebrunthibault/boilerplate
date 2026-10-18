"""LLM task declaration: what to ask (system prompt, output type) and to which model tier.

A task is declared at module level and resolves nothing at import time: the model is read from
the environment on the first run only, so an app that never calls an LLM starts without any
``LLM_MODEL_*`` configured.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from api.infra.llm.config import LlmCall

# Silence the pydantic-ai startup banner printed on stderr (noise in logs and tests).
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

OutputT = TypeVar("OutputT")
Tier = Literal["small", "medium"]


@dataclass(frozen=True)
class LlmTask(Generic[OutputT]):
    """One kind of LLM call. ``name`` is the journal key (filter in the admin screen).

    ``output_type`` is a pydantic model (structured output) or ``str`` (free text).
    """

    name: str
    system_prompt: str
    output_type: type[OutputT]
    tier: Tier = "small"
    timeout_s: float = LlmCall.TIMEOUT_S


def get_model(tier: Tier) -> str:
    """Model string (``provider:model``) of a tier, from ``LLM_MODEL_SMALL`` / ``_MEDIUM``."""
    env_key = f"LLM_MODEL_{tier.upper()}"
    value = os.environ.get(env_key)
    if not value:
        raise RuntimeError(f"{env_key} is not set — configure it in .env")
    return value


def llm_settings(timeout_s: float) -> ModelSettings:
    """Settings common to every agent: determinism, latency guard, output cap."""
    return {
        "temperature": LlmCall.TEMPERATURE,
        "timeout": timeout_s,
        "max_tokens": LlmCall.MAX_OUTPUT_TOKENS,
    }


# One agent per (task, model): the model string is part of the key so that changing
# LLM_MODEL_* (tests, scripts) never serves an agent built for another model.
_agents: dict[tuple[LlmTask[Any], str], Agent[None, Any]] = {}


def agent_for(task: LlmTask[OutputT]) -> Agent[None, OutputT]:
    """The pydantic-ai agent of a task, built on first use.

    Exposed for tests: ``with agent_for(TASK).override(model=TestModel(...)):``.
    """
    model = get_model(task.tier)
    key = (task, model)
    if key not in _agents:
        _agents[key] = Agent(
            model,
            system_prompt=task.system_prompt,
            output_type=task.output_type,
            model_settings=llm_settings(task.timeout_s),
        )
    return _agents[key]
