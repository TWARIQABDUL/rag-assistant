from pypdf import PdfReader
import re
import os

def clean_extracted_text(text):
    # Replace multiple newlines or vertical spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_text_from_pdf(pdf_path):
    # Extracts text from ONE single PDF file
    reader = PdfReader(pdf_path)
    full_text = ""

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            full_text += f"\n--- PAGE {page_num} ---\n" + text

    return clean_extracted_text(full_text)

def sliding_window_chunking(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks

# ==========================================================
# NEW FUNCTION: Loops through a directory of documents
# ==========================================================
def extract_all_from_directory(directory_path, chunk_size=500, overlap=100):
    all_chunks_with_metadata = []

    print(f"[*] Scanning folder: '{directory_path}'")

    # Check if the directory actually exists
    if not os.path.exists(directory_path):
        print(f"[-] Error: Folder '{directory_path}' does not exist.")
        return all_chunks_with_metadata

    # Loop through every file in the folder
    for filename in os.listdir(directory_path):
        # Only process files that end with .pdf
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(directory_path, filename)
            print(f"  -> Extracting & Chunking: {filename}")

            try:
                # 1. Extract the text using our single-file function
                raw_text = extract_text_from_pdf(file_path)

                # 2. Slice it up into chunks
                file_chunks = sliding_window_chunking(raw_text, chunk_size, overlap)

                # 3. Save each chunk as a dictionary containing BOTH text and the source file name
                for chunk in file_chunks:
                    all_chunks_with_metadata.append({
                        "text": chunk,
                        "source_file": filename
                    })
            except Exception as e:
                print(f"  [-] Failed to process {filename}: {e}")

    print(f"[+] Complete! Extracted a total of {len(all_chunks_with_metadata)} chunks from the folder.")
    return all_chunks_with_metadata