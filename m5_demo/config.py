# App configuration and constants

EXAMPLE_QUERIES = [
    "chicken, garlic, spinach",
    "what can I make with potatoes and cheese",
    "milk, butter, salt",
    "quick breakfast with eggs"
]

DEFAULT_FILTERS = {
    "max_minutes": None,
    "min_matched_ingredients": None
}

# Assumed backend endpoint or function
GRAPH_RAG_API_URL = "http://localhost:8000/graphrag/query"
