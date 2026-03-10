import streamlit as st
from typing import List, Dict, Any


def inject_styles():
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1200px;}
        .hero {
            background: linear-gradient(135deg, rgba(255,126,95,0.20), rgba(254,180,123,0.10));
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 16px;
            padding: 18px 20px;
            margin-bottom: 14px;
        }
        .hero-title {font-size: 1.6rem; font-weight: 700; margin-bottom: 0.2rem;}
        .hero-sub {opacity: 0.9;}
        .summary-card {
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 12px;
            padding: 10px 12px;
            background: rgba(250,250,250,0.02);
            margin-bottom: 0.6rem;
        }
        .result-title {font-size: 1.1rem; font-weight: 700; margin-bottom: 0.3rem;}
        .ingredient-matched {
            display: inline-block;
            background: rgba(255, 126, 95, 0.25);
            border: 1px solid rgba(255, 126, 95, 0.55);
            border-radius: 6px;
            padding: 1px 7px;
            margin: 2px 3px;
            font-size: 0.88rem;
            font-weight: 600;
        }
        .ingredient-normal {
            display: inline-block;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 6px;
            padding: 1px 7px;
            margin: 2px 3px;
            font-size: 0.88rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def app_header():
    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">🍽️ Recipe Discovery with GraphRAG</div>
            <div class="hero-sub">Discover recipes with graph-based retrieval and grounded AI explanations. Enter ingredients or ask naturally.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def example_queries_section(example_queries: List[str]):
    st.caption("Try one of these starter prompts")
    cols = st.columns(2)
    for i, q in enumerate(example_queries):
        if cols[i % 2].button(q, key=f"ex_{i}", use_container_width=True):
            st.session_state["query"] = q
            st.session_state["auto_search"] = True


def search_input(default_query: str = "") -> str:
    return st.text_area(
        "Search query",
        value=default_query,
        key="query",
        height=100,
        placeholder="e.g. chicken, garlic, spinach or 'vegan pasta under 30 minutes'",
    )


def filters_section(filters: Dict[str, Any]):
    st.markdown("### Filters")
    max_minutes = st.slider(
        "Max prep time (minutes)",
        min_value=5, max_value=180,
        value=int(filters.get("max_minutes") or 60),
        step=5, key="max_minutes",
    )
    min_matched_ingredients = st.slider(
        "Min matched ingredients",
        min_value=1, max_value=10,
        value=int(filters.get("min_matched_ingredients") or 1),
        step=1, key="min_matched_ingredients",
    )
    return {
        "max_minutes": max_minutes,
        "min_matched_ingredients": min_matched_ingredients,
    }


def result_summary(results: List[Dict[str, Any]]):
    recipe_count = len(results)
    minutes = [r.get("minutes") for r in results if isinstance(r.get("minutes"), (int, float))]
    matched = [r.get("matched_ingredients") for r in results if isinstance(r.get("matched_ingredients"), (int, float))]

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='summary-card'><b>Recipes</b><br>{recipe_count}</div>", unsafe_allow_html=True)
    col2.markdown(
        f"<div class='summary-card'><b>Avg Time</b><br>{round(sum(minutes)/len(minutes)) if minutes else 'N/A'} min</div>",
        unsafe_allow_html=True,
    )
    col3.markdown(
        f"<div class='summary-card'><b>Avg Matches</b><br>{round(sum(matched)/len(matched), 1) if matched else 'N/A'}</div>",
        unsafe_allow_html=True,
    )


def _render_ingredients(ingredients: List[str], matched_names: List[str]) -> str:
    matched_lower = {m.strip().lower() for m in (matched_names or [])}
    pills = []
    for ing in ingredients:
        if ing.strip().lower() in matched_lower:
            pills.append(f"<span class='ingredient-matched'>✓ {ing}</span>")
        else:
            pills.append(f"<span class='ingredient-normal'>{ing}</span>")
    return "".join(pills)


def results_section(results: List[Dict[str, Any]]):
    if not results:
        st.info("No recipes found. Try different ingredients or filters.")
        return

    result_summary(results)

    for i, dish in enumerate(results, start=1):
        with st.container(border=True):
            title = dish.get("name") or dish.get("recipe") or "Unnamed Recipe"
            st.markdown(f"<div class='result-title'>{i}. {title}</div>", unsafe_allow_html=True)

            cols = st.columns([2, 1, 1.3])
            cols[0].markdown(f"**Cuisine:** {dish.get('cuisine', 'N/A')}")
            cols[1].markdown(f"**Time:** {dish.get('minutes', 'N/A')} min")
            cols[2].markdown(f"**Matched Ingredients:** {dish.get('matched_ingredients', 0)}")

            all_ingredients = dish.get("ingredients", [])[:12]
            matched_names = dish.get("matched_ingredient_names") or []
            if all_ingredients:
                pills_html = _render_ingredients(all_ingredients, matched_names)
                st.markdown(f"**Key Ingredients:** {pills_html}", unsafe_allow_html=True)
            else:
                st.markdown("**Key Ingredients:** N/A")

            steps = dish.get("steps") or []
            if steps:
                st.markdown("**How to make it:**")
                for idx, step in enumerate(steps[:8], start=1):
                    st.markdown(f"{idx}. {step}")

            if dish.get("relevance") is not None:
                st.progress(float(dish["relevance"]), text="Relevance score")

            with st.expander("Details"):
                st.json(dish)
