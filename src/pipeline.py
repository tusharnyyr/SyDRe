import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))  # allows src modules to import each other
import zipfile
import shutil
import tempfile
import re
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from extractor import extract_text_from_pdf
from ocr_engine import ocr_pdf_pages
from embedder import generate_embeddings
from ranker import rank_pages
from cache import load_page_cache, save_page_cache

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("sydre.pipeline")

logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)

# --- Bid document detection ---
BID_DOC_SIGNALS = [
    "buyer added bid specific",
    "option clause: the purchaser reserves",
    "scope of supply (bid price",
    "general terms and conditions of contract",
    "bid specific terms and conditions",
    "bidder financial standing: the bidder should not be under liquidation",
    "consignee's location in case of carry-in warranty",
]

MIN_OCR_QUALITY_RATIO = 0.4
REAL_WORD_PATTERN = re.compile(r"[a-zA-Z]{2,}")
MAX_EMBED_CHARS = 1000


def _is_bid_document_page(text: str) -> bool:
    text_lower = text.lower()
    return any(signal in text_lower for signal in BID_DOC_SIGNALS)


def _ocr_quality_score(text: str) -> float:
    if not text:
        return 0.0
    tokens = text.split()
    if not tokens:
        return 0.0
    real_words = sum(1 for t in tokens if REAL_WORD_PATTERN.search(t))
    return real_words / len(tokens)


def run_pipeline(zip_path: str, rules: list[dict], top_n: int = 5) -> list[dict]:
    zip_path = Path(zip_path)
    vendor_id = zip_path.stem
    run_log = []

    log.info(f"Starting SyDRe run")
    log.info(f"Vendor ZIP : {zip_path.name}")
    log.info(f"Vendor ID  : {vendor_id}")
    log.info(f"Rules      : {len(rules)}")
    log.info(f"Top N      : {top_n}")

    # --- Validate ZIP ---
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")

    if zip_path.stat().st_size == 0:
        raise ValueError(f"ZIP file is empty: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.testzip()
    except zipfile.BadZipFile:
        raise zipfile.BadZipFile(f"ZIP file is corrupt or not a valid ZIP: {zip_path}")

    # ── CACHE CHECK ─────────────────────────────────────────────────────────────
    # Try to load rankable_pages + page_embeddings from disk.
    # Cache key = MD5 hash of the ZIP file contents.
    # Cache HIT  → skip all extraction, OCR, and page embedding entirely.
    # Cache MISS → run full pipeline, then save to cache for next time.
    # Rules are always re-embedded (only 5-10 texts, takes < 1 second).
    cached_pages, cached_page_embeddings = load_page_cache(str(zip_path))

    if cached_pages is not None:
        log.info(f"Cache HIT — skipping extraction and page embedding")
        log.info(f"Loaded {len(cached_pages)} pages from cache")
        run_log.append(f"Cache hit: {zip_path.name} — extraction and embedding skipped")

        rankable_pages = cached_pages
        page_embeddings = cached_page_embeddings

        # Re-embed rules only (fast)
        rule_texts = [r["rule_text"] for r in rules]
        log.info(f"Embedding {len(rules)} rules...")
        rule_embeddings = generate_embeddings(rule_texts)

        log.info(f"Ranking pages per rule (Top {top_n})...")
        results = rank_pages(rules, rule_embeddings, rankable_pages, page_embeddings, top_n)
        log.info(f"Done. {len(results)} result rows generated.")
        return results, run_log

    # ── CACHE MISS — run full pipeline ──────────────────────────────────────────
    log.info("Cache MISS — running full extraction pipeline")
    run_log.append(f"Cache miss: {zip_path.name} — running full pipeline")

    tmp_dir = Path(tempfile.mkdtemp(prefix="sydre_"))
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        pdf_files = list(tmp_dir.rglob("*.pdf"))
        non_pdf_files = [f for f in tmp_dir.rglob("*") if f.is_file() and f.suffix.lower() != ".pdf"]

        for f in non_pdf_files:
            msg = f"Skipped non-PDF file: {f.name}"
            log.warning(msg)
            run_log.append(msg)

        if not pdf_files:
            raise ValueError("No PDF files found in the ZIP.")

        log.info(f"Found {len(pdf_files)} PDF file(s)")

        all_pages = []
        bid_doc_pages_excluded = 0
        ocr_garbage_pages_excluded = 0

        # ── OPTIMISATION 1: Parallel PDF extraction ─────────────────────────────
        def _extract_one_pdf(pdf_file):
            try:
                import pdfplumber
                with pdfplumber.open(pdf_file) as pdf:
                    if pdf.doc.is_encrypted:
                        return pdf_file, [], f"Skipped encrypted PDF: {pdf_file.name}"
            except Exception:
                pass

            try:
                pages = extract_text_from_pdf(str(pdf_file), vendor_id)
            except Exception as e:
                return pdf_file, [], f"ERROR extracting {pdf_file.name}: {e}"

            if not pages:
                return pdf_file, [], f"Skipped zero-page PDF: {pdf_file.name}"

            return pdf_file, pages, f"OK: {pdf_file.name} — {len(pages)} page(s) extracted"

        log.info("Extracting PDFs in parallel...")
        pdf_to_pages = {}

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_pdf = {executor.submit(_extract_one_pdf, pdf): pdf for pdf in pdf_files}
            for future in as_completed(future_to_pdf):
                pdf_file, pages, msg = future.result()
                log.info(f"  {msg}")
                run_log.append(msg)
                if pages:
                    pdf_to_pages[pdf_file] = pages
                    all_pages.extend(pages)

        # ── OPTIMISATION 2: Early bid doc filtering BEFORE OCR ──────────────────
        # ── OPTIMISATION 3: Parallel OCR ────────────────────────────────────────
        for pdf_file, pages in pdf_to_pages.items():
            ocr_needed = [
                p for p in pages
                if p["source_type"] == "OCR"
                and not _is_bid_document_page(p.get("extracted_text", ""))
            ]

            if not ocr_needed:
                continue

            log.info(f"  → {len(ocr_needed)} page(s) in {pdf_file.name} routed to OCR (parallel)")
            ocr_page_numbers = [p["page_number"] for p in ocr_needed]

            try:
                ocr_results = ocr_pdf_pages(str(pdf_file), ocr_page_numbers)
            except Exception as e:
                log.warning(f"  OCR batch failed for {pdf_file.name}: {e}")
                ocr_results = {pn: "" for pn in ocr_page_numbers}

            for page in ocr_needed:
                ocr_text = ocr_results.get(page["page_number"], "")
                page["extracted_text"] = ocr_text
                quality = _ocr_quality_score(ocr_text)
                page["ocr_quality"] = round(quality, 2)

                if quality < MIN_OCR_QUALITY_RATIO:
                    page["source_type"] = "OCR-LowQuality"
                elif len(ocr_text) < 10:
                    page["source_type"] = "OCR-Blank"

        # --- Final filter ---
        rankable_pages = []
        for page in all_pages:
            text = page["extracted_text"]
            if not text or len(text) < 10:
                continue
            if page["source_type"] in ("OCR-LowQuality", "OCR-Blank"):
                ocr_garbage_pages_excluded += 1
                continue
            if _is_bid_document_page(text):
                bid_doc_pages_excluded += 1
                continue
            rankable_pages.append(page)

        log.info(f"Total pages indexed        : {len(all_pages)}")
        log.info(f"Bid document pages excluded: {bid_doc_pages_excluded}")
        log.info(f"Pure garbage OCR excluded  : {ocr_garbage_pages_excluded}")
        log.info(f"Rankable pages             : {len(rankable_pages)}")

        if not rankable_pages:
            raise ValueError(
                "No rankable pages after filtering.\n"
                "Possible causes: all PDFs are encrypted, corrupt, or only contain bid documents."
            )

        # ── OPTIMISATION 4: Text truncation before embedding ────────────────────
        # ── OPTIMISATION 5: Single-pass combined embedding ──────────────────────
        page_texts = [p["extracted_text"][:MAX_EMBED_CHARS] for p in rankable_pages]
        rule_texts = [r["rule_text"] for r in rules]

        log.info(f"Embedding {len(rankable_pages)} pages + {len(rules)} rules in single pass...")
        combined_texts = page_texts + rule_texts
        combined_embeddings = generate_embeddings(combined_texts)

        page_embeddings = combined_embeddings[:len(page_texts)]
        rule_embeddings = combined_embeddings[len(page_texts):]

        # ── SAVE TO CACHE ────────────────────────────────────────────────────────
        # Save rankable_pages + page_embeddings so the next run on this ZIP
        # skips straight to rule embedding and ranking.
        log.info("Saving page cache to disk...")
        save_page_cache(str(zip_path), rankable_pages, page_embeddings)
        run_log.append(f"Cache saved: {zip_path.name} — future runs will skip extraction")

        log.info(f"Ranking pages per rule (Top {top_n})...")
        results = rank_pages(rules, rule_embeddings, rankable_pages, page_embeddings, top_n)

        log.info(f"Done. {len(results)} result rows generated.")
        return results, run_log

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)