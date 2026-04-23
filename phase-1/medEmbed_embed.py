from sentence_transformers import SentenceTransformer
import numpy as np

sentences = ["The patient exhibited severe diaphoresis and tachycardia", "The person was sweating heavily with a fast heart rate"]

model = SentenceTransformer("abhinand/MedEmbed-large-v0.1")
embeddings = model.encode(sentences)


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


similarity = cosine_similarity(embeddings[0], embeddings[1])

print(similarity)

