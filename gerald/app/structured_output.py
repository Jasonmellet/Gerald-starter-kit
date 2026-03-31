"""
Shared structured output helper for LLM responses.
Parses JSON from raw text (strips fences, extracts blob), optionally repairs with a second call, validates with Pydantic.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel

from .logging import get_logger


logger = get_logger(__name__)

def get_debug_dir() -> Path:
    """Default debug output dir (gerald/outputs/debug)."""
    return Path(__file__).resolve().parent.parent / "outputs" / "debug"


@dataclass
class StructuredOutputStats:
    success: bool = False
    repaired: bool = False
    parse_failures: int = 0
    validation_failures: int = 0
    raw_saved_path: str | None = None


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences like ```json ... ``` or ``` ... ```."""
    text = text.strip() if text else ""
    if not text:
        return ""
    # Match ``` optional lang \n content ```
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def extract_first_json(text: str) -> str | None:
    """
    Find the first substring that looks like a JSON object {...} or array [...].
    Uses bracket matching so nested structures work. Returns the substring or None.
    """
    text = text.strip()
    if not text:
        return None
    open_to_close = {"{": "}", "[": "]"}
    stack: list[tuple[str, int]] = []  # (char, start_pos)
    for i, c in enumerate(text):
        if c in open_to_close:
            if not stack:
                stack.append((c, i))
            else:
                stack.append((c, i))
        elif c in ("}", "]"):
            if not stack:
                continue
            open_c, start = stack[-1]
            if open_to_close.get(open_c) == c:
                stack.pop()
                if not stack:
                    return text[start : i + 1]
    return None


def normalize_and_parse(raw: str) -> tuple[Any | None, bool]:
    """
    Try direct parse, then strip fences and parse, then extract first JSON and parse.
    Returns (parsed_value, used_extraction) where used_extraction is True if we had to strip/extract.
    """
    # 1. Direct
    try:
        return (json.loads(raw), False)
    except json.JSONDecodeError:
        pass
    # 2. Strip fences then direct
    stripped = strip_code_fences(raw)
    try:
        return (json.loads(stripped), True)
    except json.JSONDecodeError:
        pass
    # 3. Extract first JSON blob
    blob = extract_first_json(stripped if stripped else raw)
    if blob:
        try:
            return (json.loads(blob), True)
        except json.JSONDecodeError:
            pass
    return (None, False)


def repair_json_with_llm(
    raw: str,
    schema_hint: str,
    complete_fn: Callable[[str, str], str],
) -> str:
    """
    One repair pass: ask the cheap model to fix malformed text into valid JSON.
    Returns the model's raw response (caller should parse/validate again).
    """
    system = (
        "You fix malformed JSON. You receive text that was supposed to be valid JSON but is broken. "
        "Return ONLY valid JSON. No markdown, no code fences, no explanation before or after. "
        "Fix truncation, unescaped quotes, missing commas, or trailing commas."
    )
    user = (
        f"Required shape: {schema_hint}\n\n"
        "Malformed text to fix:\n---\n"
        f"{raw[:8000]}"
    )
    return complete_fn(system, user)


def save_debug_raw(raw: str, step_name: str, debug_dir: Path) -> Path:
    """Write raw response to outputs/debug/step_name_YYYYMMDD_HHMMSS.txt. Returns path."""
    debug_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_step = re.sub(r"[^\w-]", "_", step_name)
    path = debug_dir / f"{safe_step}_{ts}.txt"
    path.write_text(raw or "(empty)", encoding="utf-8")
    return path


def get_structured(
    raw: str,
    *,
    schema_class: type[BaseModel],
    expect_list: bool,
    step_name: str,
    debug_dir: Path,
    repair_fn: Callable[[str], str] | None = None,
) -> tuple[Any | None, StructuredOutputStats]:
    """
    Parse raw LLM text into JSON, optionally repair once, validate with Pydantic.

    - expect_list: True for list of schema_class (e.g. signals), False for single object (enrichment, scoring).
    - repair_fn: if provided, called when parse fails; result is re-parsed. Signature (raw) -> str.
    - Returns (validated_result, stats). result is list[schema_class] or schema_class or None.
    """
    stats = StructuredOutputStats()
    data, used_extraction = normalize_and_parse(raw)
    if data is None:
        stats.parse_failures = 1
        if repair_fn:
            repaired_raw = repair_fn(raw)
            data, _ = normalize_and_parse(repaired_raw)
            if data is not None:
                stats.repaired = True
                stats.parse_failures = 0  # repair succeeded
        if data is None:
            stats.raw_saved_path = str(save_debug_raw(raw, step_name, debug_dir))
            return (None, stats)

    # Validate
    try:
        if expect_list:
            if not isinstance(data, list):
                stats.validation_failures = 1
                stats.raw_saved_path = str(save_debug_raw(raw, step_name, debug_dir))
                return (None, stats)
            out = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                try:
                    out.append(schema_class.model_validate(item))
                except Exception:
                    pass
            if not out and data:
                stats.validation_failures = 1
                stats.raw_saved_path = str(save_debug_raw(raw, step_name, debug_dir))
                return (None, stats)
            stats.success = True
            return (out, stats)
        else:
            if not isinstance(data, dict):
                stats.validation_failures = 1
                stats.raw_saved_path = str(save_debug_raw(raw, step_name, debug_dir))
                return (None, stats)
            obj = schema_class.model_validate(data)
            stats.success = True
            return (obj, stats)
    except Exception as e:
        stats.validation_failures = 1
        stats.raw_saved_path = str(save_debug_raw(raw, step_name, debug_dir))
        logger.debug("Structured output validation failed", extra={"step": step_name, "error": str(e)})
        return (None, stats)
