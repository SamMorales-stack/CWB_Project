"""Azure OpenAI client wrapper."""
from __future__ import annotations

import json
from functools import lru_cache

from openai import AzureOpenAI
from pydantic import BaseModel

from planner.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> AzureOpenAI:
    s = get_settings()
    # BOTTLENECK — no timeout: the openai SDK default is 600 s (10 min), so a
    # slow or unresponsive API endpoint hangs the entire Streamlit process with
    # no error until the user gives up. Always set an explicit timeout.
    return AzureOpenAI(
        api_key=s.azure_openai_api_key,
        azure_endpoint=s.azure_openai_endpoint,
        api_version=s.azure_openai_api_version,
        max_retries=1,
        timeout=60.0,
    )


def structured_completion[T: BaseModel](
    *,
    deployment: str,
    system: str,
    user: str,
    schema_model: type[T],
    temperature: float = 0.1,
) -> T:
    """Call Azure OpenAI and parse the response into the given Pydantic model.

    Retries once with a stricter prompt on validation failure.
    """
    client = get_client()

    def _call(strict_note: str = "") -> str:
        # BOTTLENECK — every call here is a synchronous network round-trip to the
        # LLM API: DNS + TLS + queuing on the provider + model inference + token
        # streaming back. Latency is dominated by model inference (10-60 s for
        # large models). Minimize calls; never call in a loop when batching works.
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system + strict_note},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        return response.choices[0].message.content or "{}"

    raw = _call()
    try:
        data = json.loads(raw)
        return schema_model.model_validate(data)
    except Exception:
        # BOTTLENECK — validation failure triggers a second full round-trip.
        # Keep prompts and schemas simple to avoid hitting this path.
        retry = _call(
            strict_note=(
                "\n\nIMPORTANT: Your previous response was invalid JSON or did not match "
                "the required schema. Return ONLY a single JSON object that exactly matches "
                "the schema described in the user message. No prose, no markdown fences."
            )
        )
        data = json.loads(retry)
        return schema_model.model_validate(data)


def chat_completion(*, deployment: str, system: str, user: str, temperature: float = 0.3) -> str:
    """Plain chat completion returning the raw string response."""
    client = get_client()
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def schema_to_user_hint(schema_model: type[BaseModel]) -> str:
    """Render a JSON-schema hint suitable for inclusion in a user prompt."""
    schema = schema_model.model_json_schema()
    schema_json = json.dumps(schema, indent=2)
    return f"\n\nRespond with a single JSON object matching this schema:\n{schema_json}"
