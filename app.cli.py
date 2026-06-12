import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from groq import Groq
from google.colab import userdata

INDEX_PATH = "faiss_index.bin"
METADATA_PATH = "chunks_meta.json"
TOP_K = 15 

print("[*] Booting up Groq Chat Engine with Conversational Memory...")

# 1. Load DB & Model
index = faiss.read_index(INDEX_PATH)
with open(METADATA_PATH, "r") as f:
    metadata = json.load(f)
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# 2. Configure Groq
groq_api_key = userdata.get('GROQ_API_KEY')
client = Groq(api_key=groq_api_key)

# ==========================================
# NEW: Initialize the Chat History Buffer
# ==========================================
chat_history = [] 
MAX_HISTORY = 3  # Keeps the last 3 exchanges to preserve context windows

print("\n========================================================")
print("  RAG SYSTEM ONLINE (With Active Chat Memory)")
print("  Type 'exit' or 'quit' to stop. 'clear' to reset memory.")
print("========================================================")

while True:
    user_query = input("\n[You]: ").strip()
    if user_query.lower() in ['exit', 'quit']:
        break
    if user_query.lower() == 'clear':
        chat_history = []
        print("[*] Memory cleared!")
        continue
    if not user_query:
        continue
        
    # Step A: Perform vector lookup
    query_vector = embed_model.encode([user_query]).astype("float32")
    distances, indices = index.search(query_vector, k=TOP_K)
    
    retrieved_context = ""
    sources_used = set()
    for i in range(TOP_K):
        chunk_idx = indices[0][i]
        if chunk_idx < len(metadata):
            chunk_data = metadata[chunk_idx]
            retrieved_context += f"\n{chunk_data['text']}\n"
            sources_used.add(chunk_data['source_file'])
            
    # ==========================================
    # NEW: Format the Chat History for the LLM
    # ==========================================
    history_context = ""
    for turn in chat_history:
        history_context += f"[User]: {turn['user']}\n[AI]: {turn['ai']}\n\n"
            
    # Step B: Build the memory-aware prompt
    system_prompt = (
        "You are an expert academic assistant. Answer the user's question based strictly on the provided context "
        "and the ongoing conversation history. If the context does not contain the answer, say 'I cannot find the answer in the provided documents.'"
    )
    
    user_content = f"""
    Conversation History:
    {history_context if history_context else 'No previous conversation history.'}
    
    Retrieved Context from Documents:
    {retrieved_context}
    
    Current Question: {user_query}
    """
    
    print("[*] Consulting local database & Groq memory...")
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.2,
        )
        ai_response = chat_completion.choices[0].message.content.strip()
        
        print(f"\n[AI]: {ai_response}")
        print(f"\n[Sources Traced]: {', '.join(sources_used)}")
        print("-" * 50)
        
        # ==========================================
        # NEW: Append this turn to memory and slide the window
        # ==========================================
        chat_history.append({"user": user_query, "ai": ai_response})
        if len(chat_history) > MAX_HISTORY:
            chat_history.pop(0) # Drop the oldest message to stay optimal
            
    except Exception as e:
        print(f"\n[-] Inference Error: {e}")