import numpy as np

DEFAULT_TOP_N = 5


def rank_pages(
    rules: list[dict],
    rule_embeddings: np.ndarray,
    pages: list[dict],
    page_embeddings: np.ndarray,
    top_n: int = DEFAULT_TOP_N,
) -> list[dict]:
    """
    For each rule, compute similarity against all page embeddings.
    Return the top_n most similar pages per rule, ranked highest first.

    SPEED OPTIMISATION vs original:
      - Replaced sklearn cosine_similarity with np.dot.
        This works because embedder.py now sets normalize_embeddings=True,
        making all vectors unit-length — dot product of unit vectors IS
        cosine similarity, but np.dot runs ~20-30% faster with no dependency.
    """
    results = []

    # Similarity matrix: shape (num_rules, num_pages)
    # np.dot is valid here because all embeddings are L2-normalised
    similarity_matrix = np.dot(rule_embeddings, page_embeddings.T)

    for rule_idx, rule in enumerate(rules):
        scores = similarity_matrix[rule_idx]

        ranked_indices = np.argsort(scores)[::-1]
        top_indices = ranked_indices[:top_n]

        for rank, page_idx in enumerate(top_indices, start=1):
            page = pages[page_idx]
            score = float(scores[page_idx])
            snippet = page["extracted_text"][:400].strip() if page["extracted_text"] else ""

            results.append({
                "rule_id":     rule["rule_id"],
                "rule_text":   rule["rule_text"],
                "rank":        rank,
                "file_name":   page["file_name"],
                "page_number": page["page_number"],
                "score":       round(score, 4),
                "source_type": page["source_type"],
                "snippet":     snippet,
                "vendor_id":   page["vendor_id"],
            })

    return results


if __name__ == "__main__":
    from embedder import generate_embeddings

    mock_rules = [
        {"rule_id": "R-01", "rule_text": "Minimum average annual turnover of 5 crore"},
    ]

    mock_pages = [
        {
            "vendor_id": "V001", "file_name": "doc.pdf", "page_number": 1,
            "extracted_text": "The company has excellent ISO certification and quality processes.",
            "source_type": "Native",
        },
        {
            "vendor_id": "V001", "file_name": "doc.pdf", "page_number": 2,
            "extracted_text": "Annual turnover for FY2022-23 was Rs. 7.2 crore. FY2021-22 was Rs. 6.8 crore.",
            "source_type": "Native",
        },
        {
            "vendor_id": "V001", "file_name": "doc.pdf", "page_number": 3,
            "extracted_text": "GST registration number: 09ABCDE1234F1Z5. Registration valid from 2018.",
            "source_type": "Native",
        },
    ]

    rule_texts = [r["rule_text"] for r in mock_rules]
    page_texts = [p["extracted_text"] for p in mock_pages]

    print("\n[ranker test] Generating embeddings for mock data...\n")
    rule_embs = generate_embeddings(rule_texts)
    page_embs = generate_embeddings(page_texts)

    results = rank_pages(mock_rules, rule_embs, mock_pages, page_embs, top_n=3)

    print(f"{'Rank':<6} {'Page':<6} {'Score':<8} {'Preview'}")
    print("-" * 70)
    for r in results:
        print(f"  {r['rank']:<4} {r['page_number']:<6} {r['score']:<8} {r['snippet'][:60]}")

    top = results[0]
    passed = top["page_number"] == 2 and top["rank"] == 1
    print(f"\nTest {'PASSED' if passed else 'FAILED'}: Page {top['page_number']} ranked #{top['rank']}")