import os
import io
import re

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# ==========================================
# EXTRACTOR SECTION
# ==========================================

# Set Tesseract path if you are on Windows (uncomment and modify if needed)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def clean_extracted_text(text):
    """Removes messy formatting, multiple spaces, and broken lines."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_pdf_master(pdf_path, dpi=300):
    """
    The Ultimate Extractor:
    1. Tries to extract digital text.
    2. If the page is a scan, falls back to Kinyarwanda OCR.
    3. Flags embedded images.
    """
    print(f"[*] Opening document: {pdf_path}")
    reader = fitz.open(pdf_path)
    combined_document_text = ""

    for page_num in range(len(reader)):
        page = reader[page_num]

        # Track 1: Try to read digital text natively
        raw_text = page.get_text()
        clean_text = clean_extracted_text(raw_text)

        # --- THE OCR FALLBACK ENGINE ---
        # If the page has almost no digital text, it's a scanned document!
        if len(clean_text) < 50:
            print(f"  -> [!] Page {page_num + 1} looks like a scan. Booting up OCR...")

            # Render the page as a high-resolution image
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))

            try:
                # Ask Tesseract to read the Kinyarwanda text from the image
                ocr_text = pytesseract.image_to_string(image, lang='kin')
                clean_text = clean_extracted_text(ocr_text)
            except pytesseract.TesseractError:
                # Fallback to English/French (Latin alphabet) if 'kin' pack is missing
                ocr_text = pytesseract.image_to_string(image, lang='eng+fra')
                clean_text = clean_extracted_text(ocr_text)

        # Track 2: Identify any standard embedded images/charts on the page
        image_descriptions = []
        images = page.get_images(full=True)
        if images:
            for img_index, _ in enumerate(images):
                # We flag the image so the LLM knows a chart or photo was here
                img_placeholder = f"[Ishusho iboneka kuri iyi pajiri: image_{img_index}]"
                image_descriptions.append(img_placeholder)

        # Compile the final text for this page
        if clean_text or image_descriptions:
            combined_document_text += f"\n--- PAJIRI {page_num + 1} ---\n"
            if clean_text:
                combined_document_text += clean_text + " "
            if image_descriptions:
                combined_document_text += " ".join(image_descriptions) + "\n"

    print(f"[+] Extraction complete for {pdf_path}!\n")
    return combined_document_text

# ==========================================
# 1. THE CHUNKER FUNCTION
# ==========================================
def semantic_word_chunker(text, chunk_size=150, overlap=30):
    """Slices text into chunks based on word count, preventing broken words."""
    words = text.split()
    total_words = len(words)

    chunks = []
    start = 0

    while start < total_words:
        end = start + chunk_size
        chunk_text = " ".join(words[start:end])

        if chunk_text.strip():
            chunks.append(chunk_text)

        start += (chunk_size - overlap)

    return chunks

# ==========================================
# 2. THE MASTER PIPELINE FUNCTION
# ==========================================
def process_entire_directory(directory_path, chunk_size=150, overlap=30):
    """Loops through a folder -> Runs OCR Extractor -> Runs Word Chunker -> Adds Metadata."""
    all_chunks_with_metadata = []

    print(f"[*] Starting Directory Pipeline: '{directory_path}'")

    if not os.path.exists(directory_path):
        print(f"[-] Error: Folder '{directory_path}' does not exist.")
        return all_chunks_with_metadata

    for filename in os.listdir(directory_path):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(directory_path, filename)
            print(f"\n========================================")
            print(f"[*] Processing File: {filename}")
            print(f"========================================")

            try:
                # Step 1: The OCR Extractor (Make sure your extract_pdf_master cell was run!)
                full_document_text = extract_pdf_master(file_path)

                if not full_document_text.strip():
                    print(f"  [!] Warning: {filename} yielded no readable text.")
                    continue

                # Step 2: The Semantic Chunker
                file_chunks = semantic_word_chunker(
                    text=full_document_text,
                    chunk_size=chunk_size,
                    overlap=overlap
                )

                # Step 3: Attach the Metadata
                for chunk in file_chunks:
                    all_chunks_with_metadata.append({
                        "text": chunk,
                        "source_file": filename
                    })

                print(f"  [+] Successfully chunked {filename} into {len(file_chunks)} blocks.")

            except Exception as e:
                print(f"  [-] Critical pipeline failure on {filename}: {e}")

    print(f"\n[+] PIPELINE COMPLETE! Ready for Database.")
    print(f"[+] Total database size: {len(all_chunks_with_metadata)} chunks.")

    return all_chunks_with_metadata

if __name__ == "__main__":
    # Test the extractor on a single file if it's run standalone
    try:
        if os.path.exists("report_gov.pdf"):
            print("[*] Running standalone extractor test...")
            test_text = extract_pdf_master("report_gov.pdf")
            print(test_text[:1000]) # Print the first 1000 characters to verify
    except Exception as e:
        print(f"Test Extractor skipped: {e}")
