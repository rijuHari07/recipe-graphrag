from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

from dotenv import load_dotenv
from parse_question import parse_question
from cypher_builder import build_cypher
from neo4j_executor import Neo4jExecutor

load_dotenv()


def format_graph_results(graph_results: List[Dict[str, Any]], question_type: str) -> str:
    print("RAW GRAPH RESULTS:", graph_results)  # Debug print
    if not graph_results:
        return "No matching rows were returned from Neo4j."

    if "error" in graph_results[0]:
        return f"Neo4j error: {graph_results[0]['error']}"

    lines: List[str] = []

    if question_type == "substitute_ingredient":
        for row in graph_results[:10]:
            lines.append(
                f"Ingredient: {row.get('ingredient')} | Substitute: {row.get('substitute')}"
            )
        return "\n".join(lines)

    if question_type == "nutrition_info":
        for row in graph_results[:10]:
            lines.append(
                "Recipe: {recipe}, Time: {minutes} min, Rating: {avg_rating}, "
                "Cuisine: {cuisine}, Calories: {calories}, Protein: {protein}g, "
                "Carbs: {carbs}g, Fat: {fat}g, Matched ingredients: {matched_ingredients}".format(
                    recipe=row.get("recipe"),
                    minutes=row.get("minutes"),
                    avg_rating=row.get("avg_rating"),
                    cuisine=row.get("cuisine"),
                    calories=row.get("calories"),
                    protein=row.get("protein"),
                    carbs=row.get("carbs"),
                    fat=row.get("fat"),
                    matched_ingredients=row.get("matched_ingredients", 0),
                )
            )
        return "\n".join(lines)

    for row in graph_results[:10]:
        steps = row.get("steps", [])
        steps_text = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
        lines.append(
            f"{row.get('recipe')}\n"
            f"Cuisine: {row.get('cuisine', 'None')}\n"
            f"Time: {row.get('minutes', 'None')} min\n"
            f"Matched Ingredients: {row.get('matched_ingredients', 0)}\n"
            f"Key Ingredients: {', '.join(row.get('ingredients', []))}\n"
            f"How to make it:\n{steps_text}\n"
        )
    return "\n\n".join(lines)


def _heuristic_answer(
    user_question: str,
    graph_results: List[Dict[str, Any]],
    question_type: str,
) -> str:
    if not graph_results or "error" in graph_results[0]:
        if graph_results and "error" in graph_results[0]:
            return f"I could not retrieve results from Neo4j: {graph_results[0]['error']}"
        return (
            "I couldn't find any matches in the graph for that question. "
            "Try relaxing the cuisine, diet, ingredient, or time constraints."
        )

    if question_type == "substitute_ingredient":
        ingredient = graph_results[0].get("ingredient")
        substitutes = [row.get("substitute") for row in graph_results if row.get("substitute")]
        if not substitutes:
            return f"I couldn't find substitute options for {ingredient}."
        return f"Possible substitutes for {ingredient}: {', '.join(substitutes)}."

    names = [row.get("recipe") for row in graph_results[:5] if row.get("recipe")]
    if not names:
        return "No matches were found."

    return f"Top matches for '{user_question}': {', '.join(names)}."


def generate_answer(
    user_question: str,
    graph_results: List[Dict[str, Any]],
    question_type: str,
    model: str = "gpt-4o-mini",
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return _heuristic_answer(user_question, graph_results, question_type)

    context = format_graph_results(graph_results, question_type)
    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a world-class recipe assistant for a cooking app. "
                        "Use ONLY the provided graph rows as ground truth. "
                        "Do not invent recipes, ingredients, substitutions, nutrition facts, or timings. "
                        "Write in clear, concise, user-friendly English with proper casing and punctuation. "
                        "Preserve recipe names in readable title casing when possible. "
                        "If no relevant rows exist, explicitly say no matching recipes were found and suggest "
                        "relaxing filters (cuisine, diet, ingredients, or max time)."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"User asked: {user_question}\n\n"
                        f"Matching rows from the recipe graph:\n{context}\n\n"
                        "Return a concise answer with this structure:\n"
                        "1) One-sentence direct answer.\n"
                        "2) Top 3-5 matches as bullet points with recipe name, time, and why it matches.\n"
                        "3) If substitutions are requested, list best alternatives clearly."
                    ),
                },
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        return _heuristic_answer(user_question, graph_results, question_type)


def _apply_filter_overrides(
    parsed: Dict[str, Any],
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not filters:
        return parsed

    merged = dict(parsed)

    cuisine = filters.get("cuisine")
    if cuisine:
        merged["cuisine"] = str(cuisine).strip()

    diet = filters.get("diet")
    if diet:
        merged["dietary_restrictions"] = [str(diet).strip().lower()]

    max_minutes = filters.get("max_minutes")
    if max_minutes not in (None, ""):
        try:
            merged["max_minutes"] = int(max_minutes)
        except (TypeError, ValueError):
            pass

    min_matched_ingredients = filters.get("min_matched_ingredients")
    if min_matched_ingredients not in (None, ""):
        try:
            merged["min_matched_ingredients"] = max(1, int(min_matched_ingredients))
        except (TypeError, ValueError):
            pass

    return merged


def answer_question(
    user_question: str,
    executor: Neo4jExecutor | None = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    owns_executor = executor is None
    executor = executor or Neo4jExecutor()

    try:
        parsed = parse_question(user_question)
        parsed = _apply_filter_overrides(parsed, filters)
        print("DEBUG: Parsed question entities:", parsed)  # Debug print
        cypher, params = build_cypher(parsed)
        print("DEBUG: Generated Cypher query:", cypher)  # Debug print
        print("DEBUG: Query parameters:", params)  # Debug print

        results = executor.execute_query(cypher, params)
        print("DEBUG: Raw results from Neo4j:", results)  # Debug print

        if results and "error" in results[0]:
            answer = f"Query failed: {results[0]['error']}"
            num_results = 0
        else:
            answer = generate_answer(user_question, results, parsed["question_type"])
            num_results = len(results)

        payload = {
            "question": user_question,
            "parsed_entities": parsed,
            "cypher_used": cypher,
            "params": params,
            "num_results": num_results,
            "raw_results": results,
            "answer": answer,
        }

        print("DEBUG: Final payload:", payload)  # Debug print
        return payload

    finally:
        if owns_executor:
            executor.close()


def _safe(value: Any) -> str:
    if value is None:
        return "-"
    return str(value)


def _print_recipe_table(results: List[Dict[str, Any]], question_type: str) -> None:
    if not results or "error" in results[0]:
        print("No tabular results available.")
        return

    if question_type == "substitute_ingredient":
        print("\nSubstitution Results")
        print("-" * 80)
        print(f"{'Ingredient':<25} {'Substitute':<25}")
        print("-" * 80)
        for row in results:
            print(f"{_safe(row.get('ingredient')):<25} {_safe(row.get('substitute')):<25}")
        return

    if question_type == "nutrition_info":
        print("\nTop Matching Recipes")
        print("-" * 140)
        print(
            f"{'Recipe':<35} {'Cuisine':<15} {'Minutes':<10} {'Protein':<10} "
            f"{'Calories':<10} {'Rating':<10} {'Matched':<8}"
        )
        print("-" * 140)
        for row in results:
            print(
                f"{_safe(row.get('recipe'))[:34]:<35} "
                f"{_safe(row.get('cuisine'))[:14]:<15} "
                f"{_safe(row.get('minutes')):<10} "
                f"{_safe(row.get('protein')):<10} "
                f"{_safe(row.get('calories')):<10} "
                f"{_safe(row.get('avg_rating')):<10} "
                f"{_safe(row.get('matched_ingredients')):<8}"
            )
        return

    print("\nTop Matching Recipes")
    print("-" * 170)
    print(
        f"{'Recipe':<35} {'Cuisine':<15} {'Minutes':<10} "
        f"{'Rating':<10} {'Matched':<8} {'Ingredients':<80}"
    )
    print("-" * 170)
    for row in results:
        ingredients = ", ".join(row.get("ingredients") or [])
        print(
            f"{_safe(row.get('recipe'))[:34]:<35} "
            f"{_safe(row.get('cuisine'))[:14]:<15} "
            f"{_safe(row.get('minutes')):<10} "
            f"{_safe(row.get('avg_rating')):<10} "
            f"{_safe(row.get('matched_ingredients')):<8} "
            f"{ingredients[:79]:<80}"
        )


def _print_structured_output(payload: Dict[str, Any]) -> None:
    print("\n" + "=" * 100)
    print("QUESTION")
    print("-" * 100)
    print(payload["question"])

    print("\nPARSED ENTITIES")
    print("-" * 100)
    print(json.dumps(payload["parsed_entities"], indent=2))

    print("\nPARAMS")
    print("-" * 100)
    print(json.dumps(payload["params"], indent=2))

    print("\nFINAL ANSWER")
    print("-" * 100)
    print(payload["answer"])

    print(f"\nNUMBER OF RESULTS: {payload['num_results']}")

    _print_recipe_table(payload["raw_results"], payload["parsed_entities"]["question_type"])


if __name__ == "__main__":
    runner = Neo4jExecutor()
    try:
        while True:
            q = input("\nEnter your recipe question (or type 'exit'): ").strip()
            if q.lower() in {"exit", "quit"}:
                break

            out = answer_question(q, executor=runner)
            _print_structured_output(out)

    finally:
        runner.close()
