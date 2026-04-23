# cross_encoder.py

from sentence_transformers import CrossEncoder
from bi_encoder import retrieve   # reuse your bi-encoder retrieval


# Load Cross-Encoder Model
print("Loading Cross-Encoder model...")
cross_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')


# Reranking Function
def rerank(query, bi_results):
    """
    query: string
    bi_results: list of (doc_text, score, idx)
    """

    print("\n--- Reranking with Cross-Encoder ---")

    # Create (query, doc) pairs
    pairs = [(query, doc_text) for (doc_text, _, _) in bi_results]

    # Predict relevance scores
    cross_scores = cross_model.predict(pairs)

    # Combine results
    combined = []
    for score, (doc_text, _, idx) in zip(cross_scores, bi_results):
        combined.append((doc_text, score, idx))

    # Sort by cross-encoder score
    reranked = sorted(combined, key=lambda x: x[1], reverse=True)

    # Print results
    for doc_text, score, _ in reranked:
        print(f"{doc_text}  |  Score: {score:.4f}")

    return reranked


# Main Test Pipeline
if __name__ == "__main__":

    test_queries = [
        "coffee that is not bad but not good",
        "product that works but not well",
        "something that is not terrible but not good",
        "service that is good but not excellent",
        "experience that is not bad but disappointing",
    ]   

    for query in test_queries:
        print("\n==============================")
        print(f"Query: {query}")

        # Step 1: Bi-Encoder Retrieval
        bi_results = retrieve(query, top_k=15)

        # Step 2: Cross-Encoder Reranking
        rerank(query, bi_results)