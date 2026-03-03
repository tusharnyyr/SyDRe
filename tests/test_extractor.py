"""
Tests for src/extractor.py
Covers: native extraction, image-based detection, page object structure
"""
import pytest
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from extractor import extract_text_from_pdf, MIN_TEXT_LENGTH


def test_native_pdf_returns_pages():
    """A native PDF should return at least one page object."""
    # Use the IndiGo ticket or any real PDF in fixtures
    fixture = Path(__file__).parent / "fixtures" / "native_sample.pdf"
    if not fixture.exists():
        pytest.skip("Fixture native_sample.pdf not found in tests/fixtures/")
    pages = extract_text_from_pdf(str(fixture), "TEST_VENDOR")
    assert len(pages) > 0


def test_page_object_has_required_fields():
    fixture = Path(__file__).parent / "fixtures" / "native_sample.pdf"
    if not fixture.exists():
        pytest.skip("Fixture native_sample.pdf not found in tests/fixtures/")
    pages = extract_text_from_pdf(str(fixture), "TEST_VENDOR")
    required_fields = {"vendor_id", "file_name", "page_number", "extracted_text", "source_type"}
    for page in pages:
        assert required_fields.issubset(page.keys()), f"Missing fields in page: {page}"


def test_vendor_id_assigned_correctly():
    fixture = Path(__file__).parent / "fixtures" / "native_sample.pdf"
    if not fixture.exists():
        pytest.skip("Fixture native_sample.pdf not found in tests/fixtures/")
    pages = extract_text_from_pdf(str(fixture), "VENDOR_XYZ")
    assert all(p["vendor_id"] == "VENDOR_XYZ" for p in pages)


def test_page_numbers_are_sequential():
    fixture = Path(__file__).parent / "fixtures" / "native_sample.pdf"
    if not fixture.exists():
        pytest.skip("Fixture native_sample.pdf not found in tests/fixtures/")
    pages = extract_text_from_pdf(str(fixture), "TEST_VENDOR")
    page_nums = [p["page_number"] for p in pages]
    assert page_nums == list(range(1, len(pages) + 1))


def test_native_pages_have_text():
    fixture = Path(__file__).parent / "fixtures" / "native_sample.pdf"
    if not fixture.exists():
        pytest.skip("Fixture native_sample.pdf not found in tests/fixtures/")
    pages = extract_text_from_pdf(str(fixture), "TEST_VENDOR")
    native_pages = [p for p in pages if p["source_type"] == "Native"]
    assert all(len(p["extracted_text"]) >= MIN_TEXT_LENGTH for p in native_pages)


def test_source_type_is_valid_enum():
    fixture = Path(__file__).parent / "fixtures" / "native_sample.pdf"
    if not fixture.exists():
        pytest.skip("Fixture native_sample.pdf not found in tests/fixtures/")
    pages = extract_text_from_pdf(str(fixture), "TEST_VENDOR")
    valid_types = {"Native", "OCR"}
    assert all(p["source_type"] in valid_types for p in pages)


def test_corrupt_pdf_returns_empty_list():
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(b"This is not a valid PDF file content")
    tmp.close()
    pages = extract_text_from_pdf(tmp.name, "TEST_VENDOR")
    assert pages == []
