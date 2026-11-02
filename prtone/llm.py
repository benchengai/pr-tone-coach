"""Provider-neutral structured-output calls.

Every LLM step goes through `complete_json`: a system prompt, a user prompt and
a strict JSON schema in, the raw JSON text out, plus usage metadata (tokens,
latency, cost in USD). Callers validate the result and do every trust-critical
check deterministically, so a provider is one function here. Only OpenAI is
wired up because it is the only key configured for this project; the shape
follows ElicitSense, where Claude and a local model sit behind the same call.
"""

from __future__ import annotations

import os
import time

from .pricing import cost_usd

DEFAULT_MODELS = {"openai": "gpt-6-luna"}
PROVIDERS = tuple(DEFAULT_MODELS)


class LLMError(RuntimeError):
    pass


def parse_model_spec(spec: str) -> tuple[str, str]:
    """'openai:gpt-6.1-sol' -> ('openai', 'gpt-6.1-sol'). A bare model name means OpenAI."""
    provider, sep, model = spec.partition(":")
    if not sep:
        return "openai", spec
    if provider not in PROVIDERS or not model:
        raise ValueError(f"model spec must be provider:model with provider in {PROVIDERS}: {spec!r}")
    return provider, model


def _openai(system: str, prompt: str, schema: dict, name: str, model: str) -> tuple[str, dict]:
    import openai

    response = openai.OpenAI().responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}},
    )
    if response.status == "incomplete":
        raise LLMError(f"response incomplete: {response.incomplete_details}")
    for item in response.output:
        if item.type == "message":
            for part in item.content:
                if part.type == "refusal":
                    raise LLMError(f"model declined the request ({part.refusal})")
    u = response.usage
    return response.output_text, {
        "provider": "openai",
        "model": response.model,
        "request_id": response._request_id,
        "input_tokens": u.input_tokens,
        "cached_input_tokens": u.input_tokens_details.cached_tokens or 0,
        "output_tokens": u.output_tokens,
        "reasoning_tokens": u.output_tokens_details.reasoning_tokens or 0,
    }


def has_key(provider: str = "openai") -> bool:
    return bool(os.environ.get("OPENAI_API_KEY")) if provider == "openai" else False


def complete_json(system: str, prompt: str, schema: dict, name: str,
                  provider: str = "openai", model: str | None = None) -> tuple[str, dict]:
    call = {"openai": _openai}[provider]
    started = time.perf_counter()
    text, meta = call(system, prompt, schema, name, model or DEFAULT_MODELS[provider])
    meta["latency_s"] = round(time.perf_counter() - started, 2)
    meta["cost_usd"] = cost_usd(provider, meta["model"], meta["input_tokens"],
                                meta["cached_input_tokens"], meta["output_tokens"])
    return text, meta
