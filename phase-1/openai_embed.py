from openai import OpenAI
import os
from dotenv import load_dotenv
import numpy as np


load_dotenv()

client = OpenAI()

response = client.embeddings.create(
    input="The patient exhibited severe diaphoresis and tachycardia",
    model="text-embedding-3-small"
)

text_embedding = response.data[0].embedding

response2 = client.embeddings.create(
    input="The person was sweating heavily with a fast heart rate",
    model="text-embedding-3-small"
)

query_embedding = response2.data[0].embedding


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


similarity = cosine_similarity(text_embedding, query_embedding)

print(similarity)