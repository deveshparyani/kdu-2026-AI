"""ChromaDB vector database client."""

from typing import Optional

import chromadb
from chromadb.config import Settings

from ..config import Config
from ..models import TextChunk


class VectorDBClient:
    """ChromaDB client for vector storage and retrieval."""
    
    def __init__(self):
        """Initialize ChromaDB client."""
        self.client = chromadb.PersistentClient(
            path=Config.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="accessibility_docs",
            metadata={"hnsw:space": "cosine"}
        )
    
    def upsert(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
        metadata: Optional[list[dict]] = None
    ) -> list[str]:
        """Store chunks with embeddings in vector DB.
        
        Args:
            chunks: List of TextChunk objects
            embeddings: List of embedding vectors
            metadata: Optional metadata for each chunk
            
        Returns:
            List of chunk IDs
        """
        if not chunks or not embeddings:
            return []
        
        # Prepare data
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        
        # Prepare metadata
        if metadata is None:
            metadata = []
            for chunk in chunks:
                meta = {
                    "source_file": chunk.source_file,
                    "token_count": chunk.token_count
                }
                if chunk.page_or_timestamp:
                    meta["page_or_timestamp"] = chunk.page_or_timestamp
                metadata.append(meta)
        
        # Upsert to ChromaDB
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadata
        )
        
        return ids
    
    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_dict: Optional[dict] = None
    ) -> list[dict]:
        """Search for similar chunks.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filter
            
        Returns:
            List of results with id, text, metadata, distance
        """
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=filter_dict
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "id": results['ids'][0][i],
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i]
            })
        
        return formatted_results
    
    def delete_by_file(self, file_id: str) -> None:
        """Delete all chunks for a specific file."""
        self.collection.delete(
            where={"source_file": file_id}
        )
    
    def count(self) -> int:
        """Get total number of chunks in database."""
        return self.collection.count()
