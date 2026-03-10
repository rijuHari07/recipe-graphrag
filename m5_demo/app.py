import streamlit as st
from components import inject_styles, app_header, example_queries_section, search_input, filters_section, results_section
from service import query_graphrag
from config import EXAMPLE_QUERIES, DEFAULT_FILTERS
from utils import show_loading, show_error, show_empty


def main():
    st.set_page_config(page_title="Recipe Discovery with GraphRAG", page_icon="🍽️", layout="wide")
    inject_styles()
    app_header()

    if "filters" not in st.session_state:
        st.session_state["filters"] = DEFAULT_FILTERS.copy()
    if "last_response" not in st.session_state:
        st.session_state["last_response"] = None

    with st.sidebar:
        filters = filters_section(st.session_state["filters"])
        if st.button("Reset filters", use_container_width=True):
            filters = DEFAULT_FILTERS.copy()

    st.session_state["filters"] = filters

    example_queries_section(EXAMPLE_QUERIES)

    col_query, col_action = st.columns([4, 1])
    with col_query:
        user_query = search_input(st.session_state.get("query", ""))
    with col_action:
        st.write("")
        st.write("")
        search_clicked = st.button("Search", type="primary", use_container_width=True)

    if search_clicked or (user_query and st.session_state.get("auto_search", False)):
        if not user_query.strip():
            show_error("Please enter a query before searching.")
            return
        with st.spinner("Searching recipes..."):
            try:
                response = query_graphrag(user_query, filters)
                st.session_state["last_response"] = response
                if "error" in response:
                    show_error(response["error"])
                elif not response.get("results"):
                    show_empty()
                else:
                    if response.get("answer"):
                        st.success(response["answer"])
                    results_section(response["results"])
            except Exception as e:
                show_error(f"Unexpected error: {e}")
    elif st.session_state.get("last_response") and st.session_state["last_response"].get("results"):
        cached = st.session_state["last_response"]
        if cached.get("answer"):
            st.success(cached["answer"])
        results_section(cached["results"])

    st.markdown("---")
    st.markdown(
        """
        **About this app:**  
        This dashboard recommends recipes using a GraphRAG (Graph Retrieval-Augmented Generation) system built on a large-scale recipe knowledge graph. Enter ingredients or a question, and the system finds relevant dishes by searching the graph and generating grounded explanations.
        """
    )

if __name__ == "__main__":
    main()
