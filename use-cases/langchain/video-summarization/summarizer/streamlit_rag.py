import streamlit as st
import ast
from rag import search_in_milvus

st.set_page_config(page_title="RAG Seach UI", layout="wide")

st.title("Video RAG Search interface")

query = st.text_input("Enter your query:", "")

if st.button("Search"):
    with st.spinner("Searching..."):
        response = search_in_milvus(query)

    if "error" in response:
        st.error(f"Search failed: {response['error']}")

    else:
        try:
            results = ast.literal_eval(response["result"])
            st.success("Results recieved!")
            st.write(results)
        except Exception as e:
            st.error(f"Failed to parse response: {e}")
