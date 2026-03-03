import hashlib
import pickle
import numpy as np
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"


def _zip_hash(zip_path: str) -> str:
    """MD5 of ZIP file contents — changes only when documents change."""
    h = hashlib.md5()
    with open(zip_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_page_cache(zip_path: str):
    """Returns (pages, embeddings) if cache hit, else (None, None)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{_zip_hash(zip_path)}.pkl"
    if cache_file.exists():
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    return None, None


def save_page_cache(zip_path: str, pages: list, embeddings: np.ndarray):
    """Save pages + embeddings to disk for reuse."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{_zip_hash(zip_path)}.pkl"
    with open(cache_file, "wb") as f:
        pickle.dump((pages, embeddings), f)