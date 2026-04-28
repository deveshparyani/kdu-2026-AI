"""Streamlit frontend for accessibility platform."""

import requests
import streamlit as st

# Backend API URL
API_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="Content Accessibility Suite",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if "conversation_id" not in st.session_state:
    response = requests.post(f"{API_URL}/chat/create")
    st.session_state.conversation_id = response.json()["conversation_id"]

if "current_file_id" not in st.session_state:
    st.session_state.current_file_id = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Title
st.title("📄 Content Accessibility Suite")
st.markdown("Upload PDFs, images, or audio files to make them accessible")

# Sidebar
with st.sidebar:
    st.header("📁 Upload File")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "jpg", "jpeg", "png", "mp3", "wav"]
    )
    
    if uploaded_file and st.button("Process File"):
        with st.spinner("Processing file..."):
            files = {"file": uploaded_file}
            response = requests.post(f"{API_URL}/upload", files=files)
            
            if response.status_code == 200:
                result = response.json()
                st.session_state.current_file_id = result["file_id"]
                st.session_state.result = result
                
                # Set current file for chat
                requests.post(
                    f"{API_URL}/chat/set-file",
                    params={
                        "conversation_id": st.session_state.conversation_id,
                        "file_id": result["file_id"]
                    }
                )
                
                st.success("File processed successfully!")
            else:
                st.error(f"Error: {response.text}")

# Main content
if "result" in st.session_state:
    result = st.session_state.result
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Summary", "📄 Transcript", "🔍 Search", "💬 Chat"])
    
    # Tab 1: Summary
    with tab1:
        st.header("Summary")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Overview")
            st.write(result["summary"])
            
            st.subheader("Key Points")
            for point in result["key_points"]:
                st.markdown(f"- {point}")
            
            st.subheader("Tags")
            st.write(" • ".join(result["tags"]))
        
        with col2:
            st.subheader("Processing Info")
            st.metric("Processing Time", f"{result['processing_time_seconds']}s")
            st.metric("Total Cost", f"${result['cost_summary']['total_cost_usd']:.6f}")
            
            st.subheader("Cost Breakdown")
            for operation, cost in result['cost_summary']['by_operation'].items():
                st.text(f"{operation}: ${cost:.6f}")
    
    # Tab 2: Transcript
    with tab2:
        st.header("Full Transcript")
        st.text_area(
            "Content",
            value=result["transcript"],
            height=500,
            disabled=True
        )
    
    # Tab 3: Search
    with tab3:
        st.header("Search Content")
        
        search_query = st.text_input("Enter your search query")
        
        if st.button("Search") and search_query:
            with st.spinner("Searching..."):
                response = requests.post(
                    f"{API_URL}/search",
                    json={
                        "query": search_query,
                        "file_id": st.session_state.current_file_id,
                        "top_k": 5
                    }
                )
                
                if response.status_code == 200:
                    results = response.json()["results"]
                    
                    if results:
                        st.subheader(f"Found {len(results)} results")
                        
                        for i, result in enumerate(results, 1):
                            with st.expander(f"Result {i} (Score: {result['similarity_score']:.3f})"):
                                st.write(result["text"])
                                st.caption(f"Source: {result['source_file']}")
                    else:
                        st.info("No results found")
                else:
                    st.error("Search failed")
    
    # Tab 4: Chat
    with tab4:
        st.header("Chat About Your Document")
        
        # Display chat history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask a question about your document"):
            # Add user message to history
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.write(prompt)
            
            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = requests.post(
                        f"{API_URL}/chat/message",
                        json={
                            "conversation_id": st.session_state.conversation_id,
                            "query": prompt
                        }
                    )
                    
                    if response.status_code == 200:
                        answer = response.json()["answer"]
                        st.write(answer)
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    else:
                        st.error("Failed to get response")

else:
    st.info("👈 Upload a file to get started")
    
    st.markdown("""
    ### Features
    - 📄 **PDF Processing**: Extract text and images from PDFs
    - 🖼️ **Image Analysis**: Describe images and extract text
    - 🎵 **Audio Transcription**: Convert speech to text
    - 🔍 **Smart Search**: Hybrid semantic + keyword search
    - 💬 **AI Chat**: Ask questions about your documents
    - 💰 **Cost Tracking**: Transparent API cost breakdown
    
    ### Supported Formats
    - PDFs (.pdf)
    - Images (.jpg, .jpeg, .png)
    - Audio (.mp3, .wav)
    """)
