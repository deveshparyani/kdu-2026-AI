"""Hybrid search combining semantic and keyword search with RRF."""

from typing import Optional

from openai import OpenAI

from ..models import SearchResult, TextChunk
from ..vector_db.chroma_client import VectorDBClient
from .bm25_index import BM25Index


class HybridSearchService:
    """Hybrid search using semantic + BM25 + RRF fusion."""
    
    def __init__(
        self,
        vector_db: VectorDBClient,
        bm25_index: BM25Index,
        openai_client: OpenAI
    ):
        """Initialize hybrid search service."""
        self.vector_db = vector_db
        self.bm25_index = bm25_index
        self.openai_client = openai_client
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        file_filter: Optional[str] = None
    ) -> list[SearchResult]:
        """Perform hybrid search with RRF fusion.
        
        Args:
            query: Search query
            top_k: Number of results to return
            file_filter: Optional file_id to filter results
            
        Returns:
            List of SearchResult objects
        """
        # Get query embedding
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=[query]
        )
        query_vector = response.data[0].embedding
        
        # Semantic search
        filter_dict = {"source_file": file_filter} if file_filter else None
        semantic_results = self.vector_db.similarity_search(
            query_vector=query_vector,
            top_k=top_k * 2,  # Get more for fusion
            filter_dict=filter_dict
        )
        
        # BM25 keyword search
        bm25_results = self.bm25_index.search(query, top_k=top_k * 2)
        
        # RRF fusion
        fused_results = self._rrf_fusion(semantic_results, bm25_results, k=60)
        
        # Convert to SearchResult format
        search_results = []
        for chunk_id, score in fused_results[:top_k]:
            # Find chunk details
            chunk_data = self._get_chunk_data(chunk_id, semantic_results, bm25_results)
            if chunk_data:
                search_results.append(SearchResult(
                    chunk_id=chunk_id,
                    text=chunk_data["text"],
                    source_file=chunk_data["source_file"],
                    page_or_timestamp=chunk_data.get("page_or_timestamp"),
                    similarity_score=score,
                    context_window=chunk_data["text"][:200] + "..."
                ))
        
        return search_results
    
    def _rrf_fusion(
        self,
        semantic_results: list[dict],
        bm25_results: list[tuple[TextChunk, float]],
        k: int = 60
    ) -> list[tuple[str, float]]:
        """Reciprocal Rank Fusion algorithm."""
        scores = {}
        
        # Add semantic scores
        for rank, result in enumerate(semantic_results, start=1):
            chunk_id = result["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
        
        # Add BM25 scores
        for rank, (chunk, _) in enumerate(bm25_results, start=1):
            chunk_id = chunk.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
        
        # Sort by fused score
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results
    
    def _get_chunk_data(
        self,
        chunk_id: str,
        semantic_results: list[dict],
        bm25_results: list[tuple[TextChunk, float]]
    ) -> Optional[dict]:
        """Get chunk data from results."""
        # Check semantic results
        for result in semantic_results:
            if result["id"] == chunk_id:
                return {
                    "text": result["text"],
                    "source_file": result["metadata"]["source_file"],
                    "page_or_timestamp": result["metadata"].get("page_or_timestamp")
                }
        
        # Check BM25 results
        for chunk, _ in bm25_results:
            if chunk.chunk_id == chunk_id:
                return {
                    "text": chunk.text,
                    "source_file": chunk.source_file,
                    "page_or_timestamp": chunk.page_or_timestamp
                }
        
        return None
