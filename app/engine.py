import os
import json
import time
import faiss
import numpy as np

from google import genai
from google.genai import types
from dotenv import load_dotenv
import tempfile
import asyncio
from extractor import extract_pdf_master, semantic_word_chunker # Assuming extractor.py is in the same directory or accessible
# ==========================================
# GLOBAL INITIALIZATION (Runs only once)
# ==========================================
load_dotenv()
gemini_key = os.environ.get('GEMINI_API_KEY')
if not gemini_key:
    print("[-] ERROR: Please set the 'GEMINI_API_KEY' environment variable.")
    exit(1)

client = genai.Client(api_key=gemini_key)

INDEX_PATH = "faiss_index.bin"
METADATA_PATH = "chunks_meta.json"

if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
    print("[*] Loading FAISS Index and Metadata into memory...")
    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)
else:
    print("[-] WARNING: FAISS index or metadata not found!")
    index, metadata = None, None

# ==========================================
# THE RAG PIPELINE (Runs on every API call)
# ==========================================
def run_rag_pipeline(query: str, max_results: int):
    if not index or not metadata:
        raise Exception("Database not loaded. Ensure FAISS files exist.")
        
    start_time = time.time()
    
    stop_words = ["iyi", "raporo", "ivuga", "iki", "ku", "kuri", "niki", "ni", "bivuga", "yakoze", "?", "ese", "mbese"]
    
    system_instruction = (
        "You are an expert Rwandan government and data assistant. "
        "Your task is to respond based STRICTLY on the provided context. "
        "IMPORTANT RULES:\n"
        "1. If the user asks in Kinyarwanda, You MUST write your response in pure, fluent KINYARWANDA. Do NOT mix in Swahili.\n. If the user asks in English, reply in English.\n"
        "2. If the user asks a question, answer it ONLY if the context provides a clear explanation. \n"
        "3. CRITICAL: If the context only mentions the topic as a title, acronym, or in a Table of Contents, "
        "BUT does not actually explain what it is, YOU MUST REFUSE TO GUESS. "
        "Say exactly: 'Simbasha kubona ibisobanuro birambuye kuri iyi ngingo mu nyandiko.'\n"
        "4. Ignore text like '[Ishusho iboneka kuri iyi pajiri...]'."
    )

    try:
        # Step A: Embed Query
        query_result = client.models.embed_content(
            model="gemini-embedding-2",
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        query_vector = np.array([query_result.embeddings[0].values]).astype("float32")
        
        # Step B: Vector Search
        distances, indices = index.search(query_vector, k=max_results)

        retrieved_context = ""
        sources_used = [] # Changed from set() to list of dicts to match FastAPI schema
        retrieved_chunk_indices = set()

        # 1. FAISS Results
        for i in range(max_results):
            chunk_idx = indices[0][i]
            if chunk_idx < len(metadata):
                retrieved_chunk_indices.add(chunk_idx)
                chunk_data = metadata[chunk_idx]
                retrieved_context += f"\n[VECTOR MATCH] {chunk_data['text']}\n"
                
                # Append to our sources list
                sources_used.append({
                    "id": str(chunk_idx),
                    "title": chunk_data.get('source_file', 'Unknown Document'),
                    "content_snippet": chunk_data['text'][:150] + "...", # Just a snippet
                    "score": float(distances[0][i])
                })

        # 2. Keyword Fallback
        query_words = query.lower().replace("?", " ").split()
        filtered_words = [word for word in query_words if word not in stop_words]
        exact_keyword = " ".join(filtered_words).strip()
        
        if len(exact_keyword) > 3:
            for idx, chunk_data in enumerate(metadata):
                if exact_keyword in chunk_data['text'].lower():
                    if idx not in retrieved_chunk_indices:
                        retrieved_context += f"\n[KEYWORD MATCH (Chunk {idx})] {chunk_data['text']}\n"
                        retrieved_chunk_indices.add(idx)
                        
                        sources_used.append({
                            "id": str(idx),
                            "title": chunk_data.get('source_file', 'Unknown Document'),
                            "content_snippet": chunk_data['text'][:150] + "...",
                            "score": 1.0 # Give keyword matches a perfect score
                        })
                        
                        if len(retrieved_chunk_indices) > max_results + 5:
                            break

        # Step C: Gemini Generation
        full_prompt = f"""
        Amakuru yavuye mu nyandiko (Context):
        {retrieved_context}

        Icyasabwe (Current Input): {query}
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            )
        )

        # Return the exact schema FastAPI expects
        return {
            "answer": response.text.strip(),
            "sources": sources_used,
            "execution_time_seconds": round(time.time() - start_time, 3)
        }

    except Exception as e:
        print(f"\n[-] Inference Error: {e}")
        raise e

    # finally:
    #     # Cleanup temporary files if needed
    #     if 'temp_file' in locals():
    #         os.remove(temp_file)

def add_pdf_to_index(temp_file_path: str, original_filename: str, chunk_size: int = 150, overlap: int = 30):
    """
    Takes a PDF path, extracts text (with OCR), chunks it, embeds it, 
    and appends it to the live FAISS index.
    """
    global index, metadata
    
    # 1. Extraction (Using your Ultimate Extractor)
    print(f"[*] Starting extraction for {original_filename}...")
    full_text = extract_pdf_master(temp_file_path)
    
    if not full_text.strip():
        raise ValueError("No readable text found in the uploaded document.")

    # 2. Chunking (Using your Semantic Chunker)
    chunks = semantic_word_chunker(full_text, chunk_size=chunk_size, overlap=overlap)
    print(f"[*] Created {len(chunks)} chunks. Embedding...")

    new_embeddings = []
    new_metadata = []

    # 3. Embedding (With basic batching/rate limit handling)
    for idx, chunk_text in enumerate(chunks):
        try:
            result = client.models.embed_content(
                model="gemini-embedding-2",
                contents=chunk_text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            new_embeddings.append(result.embeddings[0].values)
            new_metadata.append({
                "source_file": original_filename,
                "text": chunk_text
            })
            time.sleep(0.2) # Basic pacing to avoid hitting rate limits instantly
        except Exception as e:
            print(f"[-] Error embedding chunk {idx}: {e}")
            # In a robust production environment, you'd add the retry logic here
            continue 

    if not new_embeddings:
        raise Exception("Failed to generate embeddings for the document.")

    # 4. Appending to FAISS
    embeddings_array = np.array(new_embeddings).astype("float32")
    
    # Initialize index if it's completely empty
    if index is None:
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatIP(dimension) # Using Inner Product like your embedder.py
        metadata = []
        
    index.add(embeddings_array)
    metadata.extend(new_metadata)

    # 5. Save back to disk
    faiss.write_index(index, INDEX_PATH)
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
        
    return len(chunks)