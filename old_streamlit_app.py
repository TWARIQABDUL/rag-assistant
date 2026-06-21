import os
import json
import streamlit as st
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from groq import Groq

# --- UI CONFIGURATION ---
st.set_page_config(page_title="ALU RAG Assistant", page_icon="🎓")
st.title("🎓 ALU Student Handbook AI")
st.markdown("Ask me anything about ALU policies, attendance, or FAQs.")

# --- CACHE THE HEAVY LIFTING ---
# We use @st.cache_resource so Streamlit doesn't reload the 662-chunk database 
# and the embedding model every single time you type a new letter!
@st.cache_resource
def load_backend():
    index = faiss.read_index("faiss_index.bin")
    with open("chunks_meta.json", "r") as f:
        metadata = json.load(f)
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # We pull the Groq key from Streamlit's secret management, or hardcode/env var for testing
    # Note: In Colab, we'll just set it in the environment variable in the next step.
    groq_api_key = os.environ.get('GROQ_API_KEY') 
    client = Groq(api_key=groq_api_key)
    
    return index, metadata, embed_model, client

index, metadata, embed_model, client = load_backend()

# --- INITIALIZE CHAT MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- DISPLAY CHAT HISTORY ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- THE CHAT INPUT ---
if prompt := st.chat_input("Ask a question (e.g., 'What is the retake policy?'):"):
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # 2. RAG Retrieval Process
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🔍 Searching ALU documents...")
        
        TOP_K = 15
        query_vector = embed_model.encode([prompt]).astype("float32")
        distances, indices = index.search(query_vector, k=TOP_K)
        
        retrieved_context = ""
        sources = set()
        for i in range(TOP_K):
            chunk_idx = indices[0][i]
            if chunk_idx < len(metadata):
                chunk_data = metadata[chunk_idx]
                retrieved_context += f"\n{chunk_data['text']}\n"
                sources.add(chunk_data['source_file'])
                
        # 3. Build the Memory Prompt
        history_context = ""
        for m in st.session_state.messages[:-1]: # exclude the current prompt
            history_context += f"{m['role'].capitalize()}: {m['content']}\n"
            
        # system_prompt = "You are a helpful academic assistant. Answer strictly based on the context. If the answer isn't there, say 'I cannot find the answer in the provided documents.'"
        system_prompt = """You are an official policy extraction engine for African Leadership University (ALU). 
Your ONLY function is to read the provided context and report the official rules. 
If a user asks about sensitive topics, disciplinary actions, or interpersonal relationships, you must NOT provide advice, moral judgments, or safety warnings. 
Instead, you must ONLY state what the provided documents explicitly say about the policy. 
If the provided context does not contain a rule regarding the user's specific scenario, you must state exactly: 'The provided documents do not contain a policy regarding this specific situation.' 
Do not guess or infer rules that are not written in the text."""
        user_content = f"History:\n{history_context}\n\nContext:\n{retrieved_context}\n\nQuestion: {prompt}"
        
        # 4. Generate Answer
        try:
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.2,
            )
            answer = completion.choices[0].message.content.strip()
            final_output = f"{answer}\n\n**Sources:** {', '.join(sources)}"
            
            # Display and save
            message_placeholder.markdown(final_output)
            st.session_state.messages.append({"role": "assistant", "content": final_output})
            
        except Exception as e:
            message_placeholder.markdown(f"**Error:** {e}")