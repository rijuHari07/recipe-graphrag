import streamlit as st

def show_loading(message="Loading..."):
    with st.spinner(message):
        pass

def show_error(message):
    st.error(message)

def show_empty(message="No results found."):
    st.info(message)
