from sentence_transformers import SentenceTransformer, util
import torch
from docs import docs   

# Load Bi-Encoder Model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Encode Documents (only once)
print("Encoding documents...")
doc_embeddings = model.encode(
    docs,
    convert_to_tensor=True,
    show_progress_bar=True
)

# Retrieval Function
def retrieve(query, top_k=5):
    print(f"\nQuery: {query}")

    # Encode query
    query_embedding = model.encode(query, convert_to_tensor=True)

    # Compute cosine similarity
    scores = util.cos_sim(query_embedding, doc_embeddings)[0]

    # Get top-k results
    top_results = torch.topk(scores, k=top_k)

    print("\n--- Top Results (Bi-Encoder) ---")

    results = []
    for score, idx in zip(top_results[0], top_results[1]):
        doc_text = docs[idx]
        score_val = score.item()

        print(f"{doc_text}  |  Score: {score_val:.4f}")

        results.append((doc_text, score_val, idx.item()))

    return results


# Test Queries (IMPORTANT)
if __name__ == "__main__":

    test_queries = [
        "coffee that is not good",
        "product that is not bad",
        "something that works but not well",
        "experience that is not good",
        "service that is not bad",
    ]

    for q in test_queries:
        retrieve(q, top_k=5)