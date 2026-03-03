"""
Tests for src/embedder.py
Covers: shape, determinism, empty input
"""
import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from embedder import generate_embeddings


SAMPLE_TEXTS = [
    "Minimum average annual turnover of 5 crore in last 3 financial years",
    "OEM authorization certificate from original manufacturer required",
    "Valid GST registration certificate must be submitted",
]


def test_embedding_shape():
    embeddings = generate_embeddings(SAMPLE_TEXTS)
    assert embeddings.shape == (3, 384), f"Expected (3, 384), got {embeddings.shape}"


def test_single_text_shape():
    embeddings = generate_embeddings(["Single sentence test"])
    assert embeddings.shape == (1, 384)


def test_determinism():
    emb1 = generate_embeddings(SAMPLE_TEXTS)
    emb2 = generate_embeddings(SAMPLE_TEXTS)
    assert np.allclose(emb1, emb2), "Embeddings are not deterministic"


def test_different_texts_produce_different_embeddings():
    emb = generate_embeddings(["Turnover certificate", "GST registration"])
    assert not np.allclose(emb[0], emb[1]), "Different texts should produce different embeddings"


def test_empty_input_returns_empty():
    result = generate_embeddings([])
    assert result.size == 0


def test_output_is_numpy_array():
    emb = generate_embeddings(SAMPLE_TEXTS)
    assert isinstance(emb, np.ndarray)
