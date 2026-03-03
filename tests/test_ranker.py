"""
Tests for src/ranker.py
Covers: correct ranking, top N selection, result structure
"""
import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from embedder import generate_embeddings
from ranker import rank_pages


MOCK_RULES = [
    {"rule_id": "R-01", "rule_text": "Minimum average annual turnover of 5 crore"},
]

MOCK_PAGES = [
    {
        "vendor_id": "V001", "file_name": "doc.pdf", "page_number": 1,
        "extracted_text": "ISO certification and quality processes",
        "source_type": "Native",
    },
    {
        "vendor_id": "V001", "file_name": "doc.pdf", "page_number": 2,
        "extracted_text": "Annual turnover FY2022-23 was Rs. 7.2 crore. FY2021-22 was Rs. 6.8 crore.",
        "source_type": "Native",
    },
    {
        "vendor_id": "V001", "file_name": "doc.pdf", "page_number": 3,
        "extracted_text": "GST registration number: 09ABCDE1234F1Z5",
        "source_type": "Native",
    },
]


@pytest.fixture(scope="module")
def ranked_results():
    rule_embs = generate_embeddings([r["rule_text"] for r in MOCK_RULES])
    page_embs = generate_embeddings([p["extracted_text"] for p in MOCK_PAGES])
    return rank_pages(MOCK_RULES, rule_embs, MOCK_PAGES, page_embs, top_n=3)


def test_correct_page_ranks_first(ranked_results):
    top = ranked_results[0]
    assert top["page_number"] == 2, f"Expected page 2 at rank 1, got page {top['page_number']}"
    assert top["rank"] == 1


def test_result_count(ranked_results):
    assert len(ranked_results) == 3  # top_n=3, 1 rule


def test_ranks_are_sequential(ranked_results):
    ranks = [r["rank"] for r in ranked_results]
    assert ranks == [1, 2, 3]


def test_scores_descending(ranked_results):
    scores = [r["score"] for r in ranked_results]
    assert scores == sorted(scores, reverse=True)


def test_result_has_required_fields(ranked_results):
    required = {"rule_id", "rule_text", "rank", "file_name", "page_number",
                "score", "source_type", "snippet", "vendor_id"}
    for r in ranked_results:
        assert required.issubset(r.keys())


def test_scores_between_zero_and_one(ranked_results):
    for r in ranked_results:
        assert 0.0 <= r["score"] <= 1.0


def test_snippet_is_string(ranked_results):
    for r in ranked_results:
        assert isinstance(r["snippet"], str)


def test_determinism():
    rule_embs = generate_embeddings([r["rule_text"] for r in MOCK_RULES])
    page_embs = generate_embeddings([p["extracted_text"] for p in MOCK_PAGES])
    results1 = rank_pages(MOCK_RULES, rule_embs, MOCK_PAGES, page_embs, top_n=3)
    results2 = rank_pages(MOCK_RULES, rule_embs, MOCK_PAGES, page_embs, top_n=3)
    scores1 = [r["score"] for r in results1]
    scores2 = [r["score"] for r in results2]
    assert scores1 == scores2
