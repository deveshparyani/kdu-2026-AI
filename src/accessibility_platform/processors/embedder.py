"""Text embedding generation."""

from openai import OpenAI

from ..cost_tracker import CostTracker
from ..models import ProcessingState
from ..vector_db.chroma_client import VectorDBClient


def embed_chunks(
    state: ProcessingState,
    openai_client: OpenAI,
    vector_db: VectorDBClient,
    cost_tracker: CostTracker
) -> ProcessingState:
    """Generate embeddings and store in vector DB.
    
    Args:
        state: ProcessingState with chunks set
        openai_client: OpenAI client instance
        vector_db: VectorDBClient instance
        cost_tracker: CostTracker instance
        
    Returns:
        Updated ProcessingState with embedding_ids populated
    """
    try:
        if not state.chunks:
            state.error = "No chunks to embed"
            return state
        
        # Batch chunks (100 per API call)
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(state.chunks), batch_size):
            batch = state.chunks[i:i + batch_size]
            texts = [chunk.text for chunk in batch]
            
            # Call embeddings API
            response = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            
            # Extract embeddings
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
            
            # Log cost
            cost_tracker.log_api_call(
                model="text-embedding-3-small",
                operation="embedding",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=0,
                file_id=state.file_id
            )
        
        # Store in vector DB
        embedding_ids = vector_db.upsert(
            chunks=state.chunks,
            embeddings=all_embeddings
        )
        
        state.embedding_ids = embedding_ids
        return state
        
    except Exception as e:
        state.error = f"Embedding failed: {str(e)}"
        return state
