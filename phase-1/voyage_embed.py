import voyageai
from dotenv import load_dotenv
import numpy as np

load_dotenv()

vo = voyageai.Client()

texts = [
    "The person was sweating heavily with a fast heart rate",
    "The patient exhibited severe diaphoresis and tachycardia",
]

# Embed the documents
result = vo.embed(texts, model="voyage-4-large", input_type="document")

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

similarity = cosine_similarity(result.embeddings[0], result.embeddings[1])

print(similarity)

