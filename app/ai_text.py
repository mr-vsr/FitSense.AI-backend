"""Helpers for turning raw LLM output into something the API can safely return."""
import json
import re
from typing import Any


def text_of(response: Any) -> str:
    """Return plain text from a LangChain message (or anything else).

    Newer Gemini / OpenAI chat models can return ``content`` as a list of
    content blocks (``[{"type": "text", "text": "..."}, ...]``) instead of a
    plain string. Returning that list straight to the browser is what made the
    old UI print raw JSON arrays instead of the model's answer.
    """
    content = getattr(response, "content", response)
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type", "text") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts).strip()
    return str(content).strip()


_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)


def extract_json(text: str) -> Any:
    """Parse JSON out of a model reply that may be wrapped in prose or ``` fences."""
    if not isinstance(text, str):
        text = text_of(text)
    candidate = text.strip()

    fence = _FENCE.search(candidate)
    if fence:
        candidate = fence.group(1).strip()

    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = candidate.find(opener), candidate.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(candidate[start:end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError("The model response did not contain valid JSON.")


def to_number(value: Any) -> float:
    """Coerce values like ``250``, ``"250 kcal"`` or ``"12.5g"`` into floats."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else 0.0
