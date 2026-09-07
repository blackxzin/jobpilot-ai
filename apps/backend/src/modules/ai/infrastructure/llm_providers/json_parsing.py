"""Shared JSON extraction for LLM responses.

Every provider had its own copy of this parser. Models return JSON wrapped in
prose or fenced code blocks depending on the model and the day, so the parsing
is genuinely fiddly and duplicating it across six adapters meant six places to
fix whenever a new wrapping style showed up.
"""
from __future__ import annotations

import json
import re

_FENCED_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_json_response(text: str) -> dict:
    """Extract a JSON object from an LLM response.

    Tries, in order: the whole string, a fenced ```json block, and the widest
    brace-delimited span. Returns a `parse_error` dict when none of those
    yield valid JSON, so callers always get a dict.
    """
    if not text:
        return {"parse_error": "Empty response from LLM provider", "raw": ""}

    candidates = [text.strip()]

    fenced = _FENCED_JSON.search(text)
    if fenced:
        candidates.append(fenced.group(1))

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return {"parse_error": "LLM response was not valid JSON", "raw": text[:2000]}
