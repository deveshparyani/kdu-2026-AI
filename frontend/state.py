import streamlit as st


def init_state() -> None:
    defaults = {
        "chat_history": [],
        "collection_name": "",
        "last_ingest_result": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
