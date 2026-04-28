"""BM25 keyword search implementation."""

from rank_bm25 import BM25Okapi

from ..models import TextChunk


class BM25Index:
    """BM25 keyword search index."""
    
    def __init__(self):
        """Initialize BM25 index."""
        self.bm25 = None
        self.chunks = []
    
    def index_chunks(self, chunks: list[TextChunk]) -> None:
        """Index text chunks for BM25 search.
        
        Args:
            chunks: List of TextChunk objects
        """
        self.chunks = chunks
        
        # Tokenize documents (simple whitespace tokenization)
        tokenized_docs = [chunk.text.lower().split() for chunk in chunks]
        
        # Create BM25 index
        self.bm25 = BM25Okapi(tokenized_docs)
    
    def search(self, query: str, top_k: int = 5) -> list[tuple[TextChunk, float]]:
        """Search for relevant chunks using BM25.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of (chunk, score) tuples
        """
        if not self.bm25 or not self.chunks:
            return []
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k results
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = [(self.chunks[i], scores[i]) for i in top_indices]
        return results
    
    def clear(self) -> None:
        """Clear the index."""
        self.bm25 = None
        self.chunks = []
