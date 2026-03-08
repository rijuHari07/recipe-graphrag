# Knowledge Graph Schema

_Generated: 2026-02-26 21:26_

## Node Types

| Node Label | Description | Source Column(s) | Properties |
|---|---|---|---|
| Recipe | A cooking recipe | recipes dataset — direct columns | id, name, minutes, n_steps, n_ingredients, description, submitted, avg_rating, num_ratings |
| Ingredient | A food ingredient used in a recipe | ingredients list column — LLM extracts clean names | name |
| Cuisine | A culinary tradition or style | cuisine column (derived from tags in Phase 1) | name |
| DietaryRestriction | A dietary requirement or lifestyle label | tags + vegetarian/vegan/gluten_free/dairy_free columns | name |
| Tag | A descriptive label for a recipe (e.g. quick, dinner, italian) | tags list column | name |
| NutritionProfile | Nutritional breakdown of a recipe | nutrition/calories/fat/sugar/sodium/protein/sat_fat/carbs columns | calories, fat, sugar, sodium, protein, sat_fat, carbs |
| User | A person who contributed or reviewed a recipe | user_id (interactions) + contributor_id (recipes) | id, role |
| Review | A user's written review and numeric rating for a recipe | review, rating, date columns from interactions | text, rating, date |

## Relationship Types

| Relationship | From | To | How Built | Properties |
|---|---|---|---|---|
| USES_INGREDIENT | Recipe | Ingredient | LLM | minutes |
| BELONGS_TO_CUISINE | Recipe | Cuisine | LLM | minutes |
| FITS_DIET | Recipe | DietaryRestriction | LLM | minutes |
| HAS_TAG | Recipe | Tag | LLM | minutes |
| HAS_NUTRITION | Recipe | NutritionProfile | structured | minutes |
| CONTRIBUTED_BY | Recipe | User | structured | minutes |
| HAS_REVIEW | Recipe | Review | structured | minutes |
| WRITTEN_BY | Review | User | structured | none |
| RATES | Review | Recipe | structured | rating |
| SUBSTITUTES_FOR | Ingredient | Ingredient | LLM | score |

## Column Coverage

| Column | Node / Relationship |
|---|---|
| id | Recipe.id |
| name | Recipe.name |
| minutes | Recipe.minutes |
| contributor_id | User.id + Recipe-[:CONTRIBUTED_BY]->User |
| submitted | Recipe.submitted |
| tags | Tag nodes + Cuisine + DietaryRestriction (via LLM) |
| nutrition / calories / fat / sugar / sodium / protein / sat_fat / carbs | NutritionProfile node |
| n_steps | Recipe.n_steps |
| steps | Recipe property (stored as count; full steps text not a node) |
| description | Recipe.description |
| ingredients | Ingredient nodes + USES_INGREDIENT edges |
| n_ingredients | Recipe.n_ingredients |
| user_id | User.id + WRITTEN_BY edge |
| recipe_id | Links Review → Recipe via RATES edge |
| minutes | Stored on Recipe node AND as property on all Recipe edges for time-based filtering |
| date | Review.date |
| rating | Review.rating + Review-[:RATES {rating}]->Recipe |
| review | Review.text |
| avg_rating | Recipe.avg_rating |
| num_ratings | Recipe.num_ratings |