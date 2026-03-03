import pdfplumber
from pathlib import Path

MIN_TEXT_LENGTH = 50  # Characters threshold — below this, page is treated as image-based


def extract_text_from_pdf(pdf_path: str, vendor_id: str) -> list[dict]:
    """
    Extract text from every page of a PDF file.
    Returns a list of page objects — one dict per page.
    Image-based pages are flagged for OCR (text left empty here, OCR handled in pipeline).
    """
    pages = []
    pdf_path = Path(pdf_path)
    file_name = pdf_path.name

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                    text = text.strip()
                except Exception:
                    text = ""

                if len(text) >= MIN_TEXT_LENGTH:
                    source_type = "Native"
                else:
                    source_type = "OCR"  # Will be processed by OCR engine later
                    text = ""            # Clear partial/garbage text

                pages.append({
                    "vendor_id":      vendor_id,
                    "file_name":      file_name,
                    "page_number":    page_num,
                    "extracted_text": text,
                    "source_type":    source_type,
                })

    except Exception as e:
        print(f"[extractor] ERROR reading {file_name}: {e}")

    return pages


if __name__ == "__main__":
    # Quick test — replace with a real PDF path on your machine
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <path_to_pdf>")
        sys.exit(1)

    test_path = sys.argv[1]
    results = extract_text_from_pdf(test_path, vendor_id="TEST_VENDOR")

    print(f"\nExtracted {len(results)} pages from: {test_path}\n")
    for p in results[:3]:  # Show first 3 pages only
        print(f"  Page {p['page_number']} | {p['source_type']} | "
              f"{len(p['extracted_text'])} chars")
        if p["extracted_text"]:
            print(f"  Preview: {p['extracted_text'][:200]}\n")
        else:
            print(f"  (flagged for OCR)\n")