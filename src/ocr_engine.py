import pytesseract
from pdf2image import convert_from_path
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# If Tesseract is not on PATH, uncomment and set:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

import platform
POPPLER_PATH = r"C:\poppler\Library\bin" if platform.system() == "Windows" else None


def _contains_devanagari(text: str) -> bool:
    return any('\u0900' <= ch <= '\u097F' for ch in text)


def ocr_page(pdf_path: str, page_number: int) -> str:
    try:
        images = convert_from_path(
            pdf_path,
            first_page=page_number,
            last_page=page_number,
            poppler_path=POPPLER_PATH,
            dpi=200,
        )

        if not images:
            return ""

        image = images[0]

        text = pytesseract.image_to_string(image, lang="eng")
        text = text.strip()

        if _contains_devanagari(text):
            text_hin = pytesseract.image_to_string(image, lang="hin+eng")
            text = text_hin.strip()

        return text

    except Exception as e:
        print(f"[ocr_engine] ERROR on page {page_number} of {Path(pdf_path).name}: {e}")
        return ""


def ocr_pdf_pages(pdf_path: str, page_numbers: list[int]) -> dict[int, str]:
    results = {}

    def _ocr_single(page_num):
        return page_num, ocr_page(pdf_path, page_num)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_ocr_single, pn): pn for pn in page_numbers}
        for future in as_completed(futures):
            try:
                page_num, text = future.result()
                results[page_num] = text
            except Exception as e:
                page_num = futures[future]
                print(f"[ocr_engine] Thread error on page {page_num}: {e}")
                results[page_num] = ""

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python ocr_engine.py <path_to_pdf> <page_number>")
        sys.exit(1)

    pdf = sys.argv[1]
    page = int(sys.argv[2])

    print(f"\nRunning OCR on: {pdf}, page {page}\n")
    result = ocr_page(pdf, page)

    if result:
        devanagari = _contains_devanagari(result)
        print(f"Extracted {len(result)} characters")
        print(f"Hindi/Devanagari detected: {devanagari}")
        print(f"\nPreview:\n{result[:500]}")
    else:
        print("No text extracted — page may be blank or unreadable.")