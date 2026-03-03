# SyDRe — Systematic Document Retrieval

An offline semantic document retrieval engine built for procurement auditors.

## What It Does

Procurement audits on Government e-Marketplace (GeM) require manually searching
through 200–500+ pages of vendor-submitted PDFs to locate evidence for each
eligibility criterion. SyDRe eliminates the navigation bottleneck.

The auditor writes eligibility rules in plain English. SyDRe reads all vendor
PDF documents, finds the most relevant pages for each rule using semantic
similarity, and produces a structured Excel output directing the auditor
exactly where to look.

**SyDRe does not make eligibility decisions. It retrieves. The auditor decides.**

## Key Features

- Fully offline — no internet connection required after setup
- No external API calls — all processing on local CPU
- Semantic search using MiniLM-L6-v2 (384-dim embeddings)
- OCR support for scanned and image-based PDFs (English + Hindi)
- Page embedding cache — repeat runs complete in 3–5 seconds
- Structured Excel output with two sheets: Summary and Full Detail
- Browser UI (Streamlit) and command-line interface

## How It Works

1. Auditor writes eligibility rules in `rules.txt` (plain numbered list)
2. Auditor uploads vendor ZIP containing all submitted PDFs
3. SyDRe extracts text from every page (native + OCR for scanned pages)
4. Pages and rules are embedded using MiniLM-L6-v2
5. Cosine similarity ranks pages per rule
6. Top N results written to Excel with file name, page number, and score

## Tech Stack

- Python 3.8+
- sentence-transformers (all-MiniLM-L6-v2)
- pdfplumber, pdf2image, pytesseract
- openpyxl, pandas
- Streamlit

## Setup
```bash
git clone https://github.com/yourusername/SyDRe.git
cd SyDRe
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Also required:
- [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) — extract to `C:\poppler\`
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) — install and add to PATH

## Running

**Browser UI:**
```bash
streamlit run app.py
```

**Command line:**
```bash
python main.py --zip input\vendor.zip
```

## Rules Format

Edit `rules.txt` before each run. One rule per line, numbered list:
```
1. Minimum average annual turnover of 5 crore in last 3 financial years
2. OEM authorization certificate from original manufacturer
3. Valid GST registration certificate
4. Minimum 3 years experience in supply of similar goods
5. Past performance: at least one order of 25% or more of bid value
```

## Project Structure
```
SyDRe/
├── src/
│   ├── pipeline.py       # Main orchestrator
│   ├── extractor.py      # PDF text extraction
│   ├── ocr_engine.py     # Tesseract OCR
│   ├── embedder.py       # MiniLM embeddings
│   ├── ranker.py         # Cosine similarity ranking
│   ├── excel_writer.py   # Excel output
│   ├── rules_reader.py   # rules.txt parser
│   └── cache.py          # Page embedding cache
├── app.py                # Streamlit UI
├── main.py               # CLI entry point
├── rules.txt             # Edit this before each run
└── requirements.txt
```
