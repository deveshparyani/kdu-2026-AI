import cohere
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

# get the embeddings
phrases = ["The patient exhibited severe diaphoresis and tachycardia", "The person was sweating heavily with a fast heart rate"]

model = "embed-v4.0"
input_type = "search_query"

res = co.embed(
    texts=phrases,
    model=model,
    input_type=input_type,
    output_dimension=1024,
    embedding_types=["float"],
)

(text1, text2) = res.embeddings.float


def calculate_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


print(
    f"For the following sentences:\n1: {phrases[0]}\n2: {phrases[1]}n\3: The similarity score is: {calculate_similarity(text1, text2):.2f}\n"
)

