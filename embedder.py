import os
import time
import json
import faiss
import numpy as np

from google import genai
from google.genai import types
from google.genai import errors
from dotenv import load_dotenv

from extractor import process_entire_directory

if __name__ == "__main__":
    load_dotenv()
    
    # 1. Extract and chunk the documents
    all_chunks = process_entire_directory("training", chunk_size=150, overlap=30)

    # 2. Securely load the API key using environment variable
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_key:
        print("[-] ERROR: Please set the 'GEMINI_API_KEY' environment variable.")
        exit(1)

    client = genai.Client(api_key=gemini_key)

    print("[*] Booting up Fault-Tolerant Gemini Embedding Engine (gemini-embedding-2)...")

    all_embeddings = []
    idx = 0

    # Only attempt to embed if we have chunks
    if all_chunks:
        # 3. Process chunks with progressive retry logic
        while idx < len(all_chunks):
            item = all_chunks[idx]
            retries = 0
            delay = 2.0  # Initial wait time in seconds if we hit a 429

            while retries < 5:
                try:
                    result = client.models.embed_content(
                        model="gemini-embedding-2",
                        contents=item["text"],
                        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
                    )

                    # Extract and store vector
                    all_embeddings.append(result.embeddings[0].values)

                    # Print progress indicators
                    if (idx + 1) % 25 == 0 or (idx + 1) == len(all_chunks):
                        print(f"  -> Successfully embedded {idx + 1} / {len(all_chunks)} chunks...")

                    idx += 1
                    time.sleep(0.2)  # Base pacing delay
                    break  # Break out of the retry loop, move to next chunk

                except errors.APIError as e:
                    # Check if it's a rate limit error (429)
                    if e.code == 429:
                        retries += 1
                        print(f"\n[!] Rate limit hit at chunk {idx+1}. Retrying in {delay}s... (Attempt {retries}/5)")
                        time.sleep(delay)
                        delay *= 2  # Double the wait time for the next attempt
                    else:
                        print(f"\n[-] Critical API Error at chunk {idx+1}: {e}")
                        retries = 5  # Force exit
                        break
                except Exception as e:
                    print(f"\n[-] Unexpected Error at chunk {idx+1}: {e}")
                    retries = 5
                    break

            if retries == 5 and idx < len(all_chunks):
                print("\n[-] Execution stopped due to persistent errors.")
                break

        # 4. Save Vector database to disk
        if len(all_embeddings) == len(all_chunks):
            embeddings_array = np.array(all_embeddings).astype("float32")
            dimension = embeddings_array.shape[1]

            print(f"\n[*] Compiling FAISS Database (Dimensions: {dimension})...")
            index = faiss.IndexFlatIP(dimension)
            index.add(embeddings_array)

            faiss.write_index(index, "faiss_index.bin")

            with open("chunks_meta.json", "w") as f:
                json.dump(all_chunks, f)

            print(f"\n[SUCCESS] Embedded all {len(all_chunks)} chunks and permanently saved the database!")
            print(f"[+] Files generated: 'faiss_index.bin' and 'chunks_meta.json'")
        else:
            print("\n[-] Database compilation aborted. Data mismatch.")
    else:
        print("\n[*] No chunks processed. Skipping embedding generation.")
