from __future__ import annotations
import json
import re
from typing import Any, Dict, List
from dotenv import load_dotenv
import os
load_dotenv()

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

ALLOWED_QUESTION_TYPES = {
    "find_recipe",
    "substitute_ingredient",
    "nutrition_info",
}

KNOWN_CUISINES = {
    "african",
    "american",
    "asian",
    "chinese",
    "french",
    "german",
    "greek",
    "indian",
    "irish",
    "italian",
    "korean",
    "mexican",
    "middle eastern",
    "moroccan",
    "russian",
    "scandinavian",
    "thai",
}

KNOWN_DIETS = {
    "vegetarian": ["vegetarian", "meat free", "meat-free"],
    "vegan": ["vegan"],
    "gluten-free": ["gluten free", "gluten-free"],
    "dairy-free": ["dairy free", "dairy-free"],
    "low-carb": ["low carb", "low-carb"],
    "low-fat": ["low fat", "low-fat"],
    "high-protein": ["high protein", "high-protein"],
}

STOPWORDS = {
    "what", "can", "i", "make", "with", "and", "a", "an", "the", "for", "under",
    "over", "recipe", "recipes", "dish", "dishes", "meal", "meals", "dinner", "lunch",
    "breakfast", "snack", "snacks", "dessert", "desserts", "healthy", "best", "good",
    "find", "show", "me", "please", "need", "want", "something", "that", "is", "are",
    "to", "of", "substitute", "replace", "instead", "nutrition", "nutritional", "info",
    "information", "tell", "give", "quick", "easy", "in", "less", "than", "minutes",
}


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    else:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            text = match.group(0)
    return json.loads(text)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            output.append(item.strip())
    return output


def _normalize_diet(text: str) -> List[str]:
    lowered = text.lower()
    diets: List[str] = []
    for canonical, variants in KNOWN_DIETS.items():
        if any(v in lowered for v in variants):
            diets.append(canonical)
    return diets


def _normalize_cuisine(text: str) -> str | None:
    lowered = text.lower()
    for cuisine in sorted(KNOWN_CUISINES, key=len, reverse=True):
        if cuisine in lowered:
            return cuisine.title() if cuisine != "middle eastern" else "Middle Eastern"
    return None


def _extract_minutes(text: str) -> int | None:
    patterns = [
        r"under\s+(\d+)\s*minutes?",
        r"less than\s+(\d+)\s*minutes?",
        r"within\s+(\d+)\s*minutes?",
        r"in\s+(\d+)\s*minutes?",
        r"(\d+)\s*minute\b",
    ]
    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            return int(match.group(1))
    return None


import re

def _extract_substitute_target(text: str):
    text = text.lower()

    patterns = [
        r"substitute for ([a-zA-Z\s\-]+)",
        r"replace ([a-zA-Z\s\-]+)",
        r"instead of ([a-zA-Z\s\-]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            ingredient = match.group(1).strip()
            ingredient = re.sub(r"[^\w\s\-]", "", ingredient)
            return [ingredient]

    return []


def _heuristic_ingredients(text: str) -> List[str]:
    lowered = text.lower().strip(" ?!.")

    with_match = re.search(r"with\s+(.+)$", lowered)
    if with_match:
        tail = with_match.group(1)
        tail = re.split(r",| under | less than | in \d+ minutes| vegetarian| vegan| gluten free| gluten-free| dairy free| dairy-free| italian| mexican| indian| greek| french| chinese| korean", tail)[0]
        parts = re.split(r"\band\b|,", tail)
        cleaned = []
        for part in parts:
            token = re.sub(r"[^a-zA-Z\-\s]", " ", part).strip()
            token = re.sub(r"\s+", " ", token)
            if token and token not in STOPWORDS:
                cleaned.append(token)
        return _dedupe_keep_order(cleaned)

    # fallback: keep meaningful terms
    tokens = re.findall(r"[a-zA-Z][a-zA-Z\-]+", lowered)
    phrases: List[str] = []
    for tok in tokens:
        if tok not in STOPWORDS and tok not in KNOWN_CUISINES:
            phrases.append(tok)
    return _dedupe_keep_order(phrases[:5])


def _heuristic_parse(user_question: str) -> Dict[str, Any]:
    lowered = user_question.lower()
    question_type = "find_recipe"
    if any(k in lowered for k in ["substitute", "replace", "instead of"]):
        question_type = "substitute_ingredient"
    elif any(k in lowered for k in ["nutrition", "calories", "protein", "fat", "carbs"]):
        question_type = "nutrition_info"

    ingredients = _extract_substitute_target(user_question) if question_type == "substitute_ingredient" else _heuristic_ingredients(user_question)

    parsed = {
        "ingredients": ingredients,
        "cuisine": _normalize_cuisine(user_question),
        "dietary_restrictions": _normalize_diet(user_question),
        "max_minutes": _extract_minutes(user_question),
        "question_type": question_type,
    }
    return _sanitize(parsed)


def _sanitize(parsed: Dict[str, Any]) -> Dict[str, Any]:
    ingredients = parsed.get("ingredients") or []
    if isinstance(ingredients, str):
        ingredients = [ingredients]
    ingredients = _dedupe_keep_order([
        re.sub(r"\s+", " ", str(item).strip().lower()) for item in ingredients if str(item).strip()
    ])

    cuisine = parsed.get("cuisine")
    if cuisine is not None:
        cuisine = str(cuisine).strip()
        if not cuisine:
            cuisine = None

    diets = parsed.get("dietary_restrictions") or []
    if isinstance(diets, str):
        diets = [diets]
    diets = _dedupe_keep_order([
        str(item).strip().lower() for item in diets if str(item).strip()
    ])

    max_minutes = parsed.get("max_minutes")
    if max_minutes in ("", None):
        max_minutes = None
    else:
        try:
            max_minutes = int(max_minutes)
        except (TypeError, ValueError):
            max_minutes = None

    question_type = str(parsed.get("question_type") or "find_recipe").strip().lower()
    if question_type not in ALLOWED_QUESTION_TYPES:
        question_type = "find_recipe"

    return {
        "ingredients": ingredients,
        "cuisine": cuisine,
        "dietary_restrictions": diets,
        "max_minutes": max_minutes,
        "question_type": question_type,
    }


def parse_question(user_question: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Parse a natural-language recipe question into structured JSON.

    Falls back to a heuristic parser when OPENAI_API_KEY is unavailable.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return _heuristic_parse(user_question)

    client = OpenAI(api_key=api_key)
    prompt = (
        "Extract structured information from this recipe question. "
        "Return ONLY valid JSON with these keys: "
        "ingredients (list of strings, empty if none mentioned), "
        "cuisine (string or null), "
        "dietary_restrictions (list), "
        "max_minutes (integer or null), "
        "question_type (one of: find_recipe, substitute_ingredient, nutrition_info).\n\n"
        f"Question: {user_question}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured fields from recipe questions and return only JSON.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return _sanitize(_extract_json(content))
    except Exception:
        return _heuristic_parse(user_question)


if __name__ == "__main__":
    demo_questions = [
        "What can I make with chicken and rice?",
        "Vegetarian Italian dinner under 30 minutes",
        "What can I substitute for butter?",
        "High protein breakfast recipes",
        "Gluten-free Mexican dishes",
    ]
    for q in demo_questions:
        print(q)
        print(json.dumps(parse_question(q), indent=2))
        print("-" * 60)
