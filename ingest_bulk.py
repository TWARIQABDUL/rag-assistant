import os
import faiss
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from extract_pipeline import extract_all_from_directory

# 1. Updated to match your new folder name!
FOLDER_NAME = "training"

if __name__ == "__main__":
    # 2. Auto-create the folder if Colab deleted it during a restart
    if not os.path.exists(FOLDER_NAME):
        os.makedirs(FOLDER_NAME)
        print(f"[!] Created missing folder: '{FOLDER_NAME}/'")
        print(f"[!] ACTION REQUIRED: Please open the '{FOLDER_NAME}' folder on the left, upload your PDF, and re-run this cell.")
    else:
        # 3. Run the directory loader
        all_chunks = extract_all_from_directory(FOLDER_NAME, chunk_size=500, overlap=100)
        
        # 4. Strict guard flag: The math section is LOCKED inside this 'else' block
        if len(all_chunks) == 0:
            print(f"\n[-] Stop: The '{FOLDER_NAME}' folder is currently empty.")
            print("[!] Please upload at least one PDF file into that folder before running.")
        else:
            # 5. Generate the Vector Embeddings safely
            print("\n[*] Generating vector embeddings...")
            model = SentenceTransformer("all-MiniLM-L6-v2")
            
            text_list = [item["text"] for item in all_chunks]
            embeddings = model.encode(text_list, show_progress_bar=True)
            
            # Convert to numpy array safely
            embeddings = np.array(embeddings).astype("float32")
            
            # 6. Save Vector database to disk
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)
            index.add(embeddings)
            faiss.write_index(index, "faiss_index.bin")
            
            # 7. Save metadata to disk
            with open("chunks_meta.json", "w") as f:
                json.dump(all_chunks, f)
                
            print(f"\n[SUCCESS] Successfully processed files! Saved database with {len(all_chunks)} chunks.")