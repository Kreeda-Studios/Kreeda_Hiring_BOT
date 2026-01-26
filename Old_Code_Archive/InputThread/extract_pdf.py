import os
import time
import pymupdf as fitz  # PyMuPDF

INDEX_FILE = "Processed_Resume_Index.txt"

def process_pdf(pdf_path, save_dir, original_name=None):
    """
    Extract text from PDF using PyMuPDF, save as txt, and append txt path to index file.

    Args:
        pdf_path (str): input PDF file path
        save_dir (str): directory to save extracted txt
        original_name (str): original uploaded filename (optional)

    Returns:
        str or None: path to saved txt file or None if failure
    """
    try:
        os.makedirs(save_dir, exist_ok=True)

        start_time = time.time()

        # ✅ Use original uploaded name if provided, otherwise fall back to temp filename
        if original_name:
            resume_name = os.path.splitext(os.path.basename(original_name))[0]
        else:
            resume_name = os.path.splitext(os.path.basename(pdf_path))[0]

        save_path = os.path.join(save_dir, f"{resume_name}.txt")

        doc = fitz.open(pdf_path)
        all_text = []
        for page_index in range(len(doc)):
            page = doc[page_index]
            page_text = page.get_text("text")
            all_text.append(f"\n\n--- Page {page_index + 1} ---\n{page_text.strip()}")

        final_text = "\n".join(all_text).strip()

        if final_text:
            # ✅ Write/overwrite extracted text file
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(final_text)

            # ✅ Append only the txt path to index file (avoid new txt duplication)
            with open(INDEX_FILE, "a", encoding="utf-8") as idx:
                idx.write(f"{save_path}\n")

            elapsed = time.time() - start_time
            # print(f"✅ Extracted and saved: {save_path} | Time: {elapsed:.2f} sec")
            return save_path
        else:
            print(f"⚠️ No text extracted from: {pdf_path}")
            return None

    except Exception as e:
        print(f"❌ Error processing {pdf_path}: {e}")
        return None

