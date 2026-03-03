from sentence_transformers import SentenceTransformer
import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def _get_model() -> SentenceTransformer:
    """Lazy-load the model — only initialised when first needed."""
    global _model
    if _model is None:
        print(f"[embedder] Loading model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        print(f"[embedder] Model loaded.")
    return _model


def generate_embeddings(texts: list[str]) -> np.ndarray:
    """
    Convert a list of text strings to a 2D numpy array of embeddings.
    Shape: (len(texts), 384)
    Fully deterministic — identical input always produces identical output.

    SPEED OPTIMISATIONS vs original:
      - batch_size=64            : was default 32 — larger batches ~2x faster on CPU
      - normalize_embeddings=True: pre-normalises vectors so ranker uses faster
                                   np.dot instead of sklearn cosine_similarity
    """
    if not texts:
        return np.array([])

    model = _get_model()
    embeddings = model.encode(
        texts,
        batch_size=64,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings


if __name__ == "__main__":
    test_sentences = [
        "Minimum average annual turnover of 5 crore in last 3 financial years",
        "OEM authorization certificate from original manufacturer required",
        "Valid GST registration certificate must be submitted",
    ]

    print("\nGenerating embeddings for 3 test sentences...\n")
    embeddings_1 = generate_embeddings(test_sentences)
    embeddings_2 = generate_embeddings(test_sentences)

    print(f"Shape        : {embeddings_1.shape}")
    print(f"Expected     : (3, 384)")
    print(f"Shape OK     : {embeddings_1.shape == (3, 384)}")
    print(f"Deterministic: {np.allclose(embeddings_1, embeddings_2)}")
    print(f"\nFirst vector preview (first 8 dims):")
    print(f"  {embeddings_1[0][:8]}")