from typing import Dict, Any, Optional
import re
import ast

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from graphrag import answer_question


def _to_title_case(text: Any) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).title()


def _sentence_case(text: Any) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    return value[0].upper() + value[1:]


def _parse_steps(raw_steps: Any) -> list[str]:
    # Case 1: already a proper list (Neo4j returned a list property)
    if isinstance(raw_steps, list):
        cleaned = [str(step).strip() for step in raw_steps if str(step).strip()]
        return cleaned[:8]

    if isinstance(raw_steps, str) and raw_steps.strip():
        stripped = raw_steps.strip()

        # Case 2: Python list-literal string e.g. "['step one', 'step two', ...]"
        # This happens when steps were serialized via str(list) before loading into Neo4j.
        if stripped.startswith("["):
            try:
                parsed = ast.literal_eval(stripped)
                if isinstance(parsed, list):
                    cleaned = [str(s).strip() for s in parsed if str(s).strip()]
                    return cleaned[:8]
            except (ValueError, SyntaxError):
                pass

        # Case 3: plain multi-line or numbered text
        chunks = re.split(r"\n+|\s*\d+\)\s*|\s*\d+\.\s*", stripped)
        cleaned = [chunk.strip(" -•\t") for chunk in chunks if chunk.strip(" -•\t")]
        return cleaned[:8]

    return []


def _fallback_steps(row: Dict[str, Any]) -> list[str]:
    ingredients = row.get("ingredients") or []
    minutes = row.get("minutes")
    description = (row.get("description") or "").strip()

    prep_ingredients = ", ".join(ingredients[:6]) if ingredients else "the required ingredients"
    steps = [
        f"Gather and measure {prep_ingredients}.",
        "Prep ingredients by washing, chopping, and organizing them before cooking.",
    ]

    if isinstance(minutes, (int, float)) and minutes > 0:
        steps.append(f"Cook following your preferred method until done (about {int(minutes)} minutes total).")
    else:
        steps.append("Cook until the dish is fully done and flavors are combined.")

    if description:
        steps.append(f"Final touch: {description[:180]}{'...' if len(description) > 180 else ''}")
    else:
        steps.append("Taste, adjust seasoning, and serve warm.")

    return steps


def _normalize_result(row: Dict[str, Any], explanation: str) -> Dict[str, Any]:
    normalized = dict(row)
    if not normalized.get("name"):
        normalized["name"] = normalized.get("recipe") or "Unnamed Recipe"

    normalized["name"] = _to_title_case(normalized.get("name")) or "Unnamed Recipe"
    if normalized.get("recipe"):
        normalized["recipe"] = _to_title_case(normalized.get("recipe"))
    if normalized.get("cuisine"):
        normalized["cuisine"] = _to_title_case(normalized.get("cuisine"))

    # Coerce minutes to int — Neo4j may return it as a string or float
    raw_minutes = normalized.get("minutes")
    if raw_minutes not in (None, ""):
        try:
            normalized["minutes"] = int(float(str(raw_minutes)))
        except (TypeError, ValueError):
            normalized["minutes"] = None

    ingredients = normalized.get("ingredients") or []
    normalized["ingredients"] = [_to_title_case(item) for item in ingredients if str(item).strip()]

    if normalized.get("description"):
        normalized["description"] = _sentence_case(normalized.get("description"))

    recipe_steps = _parse_steps(normalized.get("steps"))
    step_list = recipe_steps if recipe_steps else _fallback_steps(normalized)
    normalized["steps"] = [_sentence_case(step) for step in step_list]

    normalized["explanation"] = _sentence_case(explanation)
    return normalized


def query_graphrag(
    user_query: str,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Directly call the backend GraphRAG pipeline to answer the user query.
    """
    if not user_query.strip():
        return {"results": []}
    try:
        payload = answer_question(user_query, filters=filters)
        raw = payload.get("raw_results")
        has_error = (
            isinstance(raw, list) and raw and "error" in raw[0]
        )
        if raw and not has_error:
            answer = payload.get("answer", "")
            results = [_normalize_result(r, answer) for r in raw]
            return {
                "results": results,
                "answer": answer,
                "meta": {
                    "num_results": payload.get("num_results", len(results)),
                    "parsed_entities": payload.get("parsed_entities", {}),
                },
            }
        elif payload.get("answer"):
            return {"error": payload["answer"]}
        else:
            return {"results": []}
    except Exception as e:
        return {"error": f"Backend error: {e}"}
