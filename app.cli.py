import os
import json
import faiss
import numpy as np

from google import genai
from google.genai import types
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    
    # 1. Securely load the API key
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_key:
        print("[-] ERROR: Please set the 'GEMINI_API_KEY' environment variable.")
        exit(1)

    client = genai.Client(api_key=gemini_key)

    # 2. Load the Local Database
    INDEX_PATH = "faiss_index.bin"
    METADATA_PATH = "chunks_meta.json"
    TOP_K = 5  # We grab the top 5 most relevant chunks

    if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
        index = faiss.read_index(INDEX_PATH)
        with open(METADATA_PATH, "r") as f:
            metadata = json.load(f)

        print("========================================================")
        print("  Kinyarwanda RAG System: GEMINI EDITION ONLINE")
        print("  Type 'exit' or 'quit' to stop. 'clear' to reset memory.")
        print("========================================================")

        # 3. The Strict Rules Engine
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

        chat_history = []
        MAX_HISTORY = 3

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

            # Step A: Embed the User's Search Query (Using RETRIEVAL_QUERY)
            try:
                query_result = client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=user_query,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
                )

                query_vector = np.array([query_result.embeddings[0].values]).astype("float32")

                # Step B: Search Local FAISS DB
                distances, indices = index.search(query_vector, k=TOP_K)

                retrieved_context = ""
                sources_used = set()
                for i in range(TOP_K):
                    chunk_idx = indices[0][i]
                    if chunk_idx < len(metadata):
                        chunk_data = metadata[chunk_idx]
                        retrieved_context += f"\n{chunk_data['text']}\n"
                        sources_used.add(chunk_data['source_file'])

                # Format History
                history_context = ""
                for turn in chat_history:
                    history_context += f"[Umukoresha (User)]: {turn['user']}\n[AI]: {turn['ai']}\n\n"

                # Step C: Package the prompt for the Chat Model
                full_prompt = f"""
                Amateka y'ibiganiro (History):
                {history_context if history_context else 'Nta biganiro byabanje.'}

                Amakuru yavuye mu nyandiko (Context):
                {retrieved_context}

                Icyasabwe (Current Input): {user_query}
                """

                print("[*] Searching FAISS and consulting Gemini 1.5 Flash...")

                # Step D: Generate the Final Answer
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                    )
                )

                ai_response = response.text.strip()

                print(f"\n[AI]: {ai_response}")
                print(f"\n[Sources Traced]: {', '.join(sources_used)}")
                print("-" * 50)

                chat_history.append({"user": user_query, "ai": ai_response})
                if len(chat_history) > MAX_HISTORY:
                    chat_history.pop(0)

            except Exception as e:
                print(f"\n[-] Inference Error: {e}")
    else:
        print("\n[-] Error: Missing faiss_index.bin or chunks_meta.json. Ensure files are embedded first by running `python embedder.py`.")