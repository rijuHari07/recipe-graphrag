from __future__ import annotations

from typing import Any, Dict, Tuple


def _common_params(parsed_entities: Dict[str, Any]) -> Dict[str, Any]:
    min_matched_ingredients = parsed_entities.get("min_matched_ingredients")
    if min_matched_ingredients in (None, ""):
        min_matched_ingredients = 1
    else:
        try:
            min_matched_ingredients = max(1, int(min_matched_ingredients))
        except (TypeError, ValueError):
            min_matched_ingredients = 1

    return {
        "ingredients": parsed_entities.get("ingredients", []) or [],
        "cuisine": parsed_entities.get("cuisine"),
        "dietary_restrictions": parsed_entities.get("dietary_restrictions", []) or [],
        "max_minutes": parsed_entities.get("max_minutes"),
        "min_matched_ingredients": min_matched_ingredients,
    }


def build_cypher(parsed_entities: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    question_type = parsed_entities.get("question_type", "find_recipe")

    if question_type == "substitute_ingredient":
        ingredient = (parsed_entities.get("ingredients") or [None])[0]
        cypher = """
        MATCH (i:Ingredient {name: $ingredient})-[:SUBSTITUTES_FOR]->(sub:Ingredient)
        RETURN i.name AS ingredient, sub.name AS substitute
        LIMIT 5
        """.strip()
        return cypher, {"ingredient": ingredient}

    if question_type == "nutrition_info":
        # FIX 1: r-side filters (minutes, diet) moved before OPTIONAL MATCH so they
        # filter Recipe rows directly. Previously bundled into the OPTIONAL MATCH WHERE,
        # which in Neo4j only nullifies c — it does NOT filter r rows.
        # FIX 2: recipe_ingredients and matched_ingredients now computed via WITH
        # before being referenced, fixing the "undefined variable" bug.
        # FIX 3: toInteger() cast handles minutes stored as strings in Neo4j.
        cypher = """
        MATCH (r:Recipe)-[:HAS_NUTRITION]->(n:NutritionProfile)
        WHERE ($max_minutes IS NULL OR toInteger(r.minutes) <= $max_minutes)
          AND (
                size($dietary_restrictions) = 0 OR
                ALL(diet IN $dietary_restrictions
                    WHERE EXISTS {
                        MATCH (r)-[:FITS_DIET]->(:DietaryRestriction {name: diet})
                    })
              )
        OPTIONAL MATCH (r)-[:BELONGS_TO_CUISINE]->(c:Cuisine)
        WHERE ($cuisine IS NULL OR c.name = $cuisine)
        OPTIONAL MATCH (r)-[:USES_INGREDIENT]->(i:Ingredient)
        WITH r, c, n, collect(DISTINCT i.name) AS recipe_ingredients
        WITH r, c, n, recipe_ingredients,
             CASE
                 WHEN size($ingredients) = 0 THEN 0
                 ELSE size([ing IN $ingredients WHERE ing IN recipe_ingredients])
             END AS matched_ingredients
        WHERE size($ingredients) = 0 OR matched_ingredients >= $min_matched_ingredients
        RETURN r.name AS recipe,
               toInteger(r.minutes) AS minutes,
               r.avg_rating AS avg_rating,
               c.name AS cuisine,
               r.description AS description,
               r.n_steps AS n_steps,
               r.n_ingredients AS n_ingredients,
               r.steps AS steps,
               n.calories AS calories,
               n.protein AS protein,
               n.carbs AS carbs,
               n.fat AS fat,
               matched_ingredients,
               recipe_ingredients[0..12] AS ingredients
        ORDER BY matched_ingredients DESC, r.avg_rating DESC, toInteger(r.minutes) ASC
        LIMIT 10
        """.strip()
        return cypher, _common_params(parsed_entities)

    # FIX: r-side filters (minutes, diet) moved to a WHERE directly after MATCH (r:Recipe).
    # Previously inside the WHERE after OPTIONAL MATCH — in Neo4j this can suppress entire
    # rows (not just nullify c) when an r-side condition fails.
    # FIX: toInteger() cast handles minutes stored as strings in Neo4j.
    cypher = """
    MATCH (r:Recipe)
    WHERE ($max_minutes IS NULL OR toInteger(r.minutes) <= $max_minutes)
      AND (
            size($dietary_restrictions) = 0 OR
            ALL(diet IN $dietary_restrictions
                WHERE EXISTS {
                    MATCH (r)-[:FITS_DIET]->(:DietaryRestriction {name: diet})
                })
          )
    OPTIONAL MATCH (r)-[:BELONGS_TO_CUISINE]->(c:Cuisine)
    WHERE ($cuisine IS NULL OR c.name = $cuisine)
    OPTIONAL MATCH (r)-[:USES_INGREDIENT]->(i:Ingredient)
    WITH r, c, collect(DISTINCT i.name) AS recipe_ingredients
    WITH r, c, recipe_ingredients,
         CASE
             WHEN size($ingredients) = 0 THEN 0
             ELSE size([ing IN $ingredients WHERE ing IN recipe_ingredients])
         END AS matched_ingredients
    WHERE size($ingredients) = 0 OR matched_ingredients >= $min_matched_ingredients
    RETURN r.name AS recipe,
           toInteger(r.minutes) AS minutes,
           r.avg_rating AS avg_rating,
           c.name AS cuisine,
           r.description AS description,
           r.n_steps AS n_steps,
           r.n_ingredients AS n_ingredients,
           r.steps AS steps,
           matched_ingredients,
           recipe_ingredients[0..12] AS ingredients
    ORDER BY matched_ingredients DESC, r.avg_rating DESC, toInteger(r.minutes) ASC
    LIMIT 10
    """.strip()

    return cypher, _common_params(parsed_entities)


if __name__ == "__main__":
    examples = [
        {
            "ingredients": ["chicken", "rice"],
            "cuisine": None,
            "dietary_restrictions": [],
            "max_minutes": None,
            "question_type": "find_recipe",
        },
        {
            "ingredients": ["butter"],
            "cuisine": None,
            "dietary_restrictions": [],
            "max_minutes": None,
            "question_type": "substitute_ingredient",
        },
        {
            "ingredients": ["mango"],
            "cuisine": None,
            "dietary_restrictions": [],
            "max_minutes": 30,
            "question_type": "find_recipe",
        },
    ]

    for example in examples:
        query, params = build_cypher(example)
        print(query)
        print(params)
        print("-" * 80)
