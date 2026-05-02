"""Gemini client wrapper using Google AI Studio's OpenAI-compatible endpoint."""
from __future__ import annotations

import json
from functools import lru_cache

from openai import OpenAI
from pydantic import BaseModel

from planner.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    s = get_settings()
    # Google AI Studio's OpenAI-compatible endpoint.
    # max_retries=3 gives automatic exponential backoff on rate-limit and transient errors.
    return OpenAI(
        api_key=s.google_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        max_retries=3,
    )


def structured_completion[T: BaseModel](
    *,
    deployment: str,
    system: str,
    user: str,
    schema_model: type[T],
    temperature: float = 0.1,
) -> T:
    """Call Gemini via Google AI Studio's OpenAI-compatible endpoint.

    Parses the response into the given Pydantic model.

    Retries once with a stricter prompt on validation failure.
    """
    client = get_client()

    def _call(strict_note: str = "") -> str:
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
