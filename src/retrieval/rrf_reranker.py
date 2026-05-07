"""
Reciprocal Rank Fusion (RRF) reranking module.

This module implements RRF algorithm to combine and rerank results
from multiple retrieval methods.
"""

from typing import List, Tuple, Dict
from langchain_core.documents import Document
from collections import defaultdict

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class RRFReranker:
    """
    Reciprocal Rank Fusion reranker.
    
    RRF is an algorithm that combines rankings from multiple sources
    by using the reciprocal of the rank positions. It's effective for
    combining results from different retrieval methods.
    
    Formula: RRF_score = Σ(1 / (k + rank_i))
    where k is a constant (default 60) and rank_i is the rank in method i
    
    Attributes:
        k: RRF constant (default 60)
    """
    
    def __init__(self, k: int = 60):
        """
        Initialize with RRF constant.
        
        Args:
            k: RRF constant (default 60). Higher values give less weight
               to top-ranked items.
        """
        self.k = k
        logger.info(f"RRFReranker initialized with k={k}")
    
    def rerank(
        self,
        results_by_method: Dict[str, List[Tuple[Document, float]]],
        top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Rerank results using RRF algorithm.
        
        This method:
        1. Collects results from all methods
        2. Removes duplicates (same chunk_id)
        3. Calculates RRF score for each unique document
        4. Sorts by RRF score (descending)
        5. Returns top-k results
        
        Args:
            results_by_method: Dictionary mapping method name to list of (Document, score) tuples
                              Example: {
                                  "bm25": [(doc1, 5.2), (doc2, 3.1)],
                                  "semantic": [(doc1, 0.9), (doc3, 0.8)],
                                  "graph": [(doc2, 1.0)]
                              }
            top_k: Number of top results to return (default: 5)
            
        Returns:
            List[Tuple[Document, float]]: List of (Document, rrf_score) tuples.
                                         Sorted by RRF score (highest first).
            
        Example:
            >>> reranker = RRFReranker(k=60)
            >>> results = {
            ...     "bm25": [(doc1, 5.0), (doc2, 3.0)],
            ...     "semantic": [(doc1, 0.9), (doc3, 0.8)]
            ... }
            >>> reranked = reranker.rerank(results, top_k=2)
            >>> for doc, score in reranked:
            ...     print(f"RRF Score: {score:.4f}")
        """
        logger.info(f"Reranking results from {len(results_by_method)} methods")
        
        # Step 1: Collect all unique documents with their ranks in each method
        # Use chunk_id as unique identifier
        doc_ranks = defaultdict(list)  # Maps chunk_id to list of (method, rank) tuples
        doc_map = {}  # Maps chunk_id to Document object
        
        for method_name, results in results_by_method.items():
            logger.debug(f"Processing {len(results)} results from {method_name}")
            
            for rank, (doc, score) in enumerate(results, start=1):
                # Get unique identifier for document
                chunk_id = doc.metadata.get("chunk_id", id(doc))
                
                # Store rank for this method
                doc_ranks[chunk_id].append((method_name, rank))
                
                # Store document object (use first occurrence)
                if chunk_id not in doc_map:
                    doc_map[chunk_id] = doc
        
        logger.info(f"Found {len(doc_ranks)} unique documents across all methods")
        
        # Step 2: Calculate RRF score for each document
        rrf_scores = {}
        
        for chunk_id, ranks in doc_ranks.items():
            # Calculate RRF score: sum of 1/(k + rank) for all methods
            rrf_score = sum(1.0 / (self.k + rank) for method, rank in ranks)
            rrf_scores[chunk_id] = rrf_score
            
            logger.debug(
                f"Document {chunk_id}: ranks={ranks}, RRF score={rrf_score:.4f}"
            )
        
        # Step 3: Sort by RRF score (descending) and get top-k
        sorted_chunk_ids = sorted(
            rrf_scores.keys(),
            key=lambda cid: rrf_scores[cid],
            reverse=True
        )[:top_k]
        
        # Step 4: Create final results list
        final_results = [
            (doc_map[chunk_id], rrf_scores[chunk_id])
            for chunk_id in sorted_chunk_ids
        ]
        
        logger.info(f"Reranking complete: returning top {len(final_results)} results")
        
        if final_results:
            logger.debug(f"Top RRF score: {final_results[0][1]:.4f}")
        
        return final_results
    
    def get_rrf_score(self, ranks: List[int]) -> float:
        """
        Calculate RRF score for a document given its ranks in different methods.
        
        Args:
            ranks: List of rank positions (1-indexed) from different methods
            
        Returns:
            float: RRF score
            
        Example:
            >>> reranker = RRFReranker(k=60)
            >>> score = reranker.get_rrf_score([1, 3, 2])  # Ranks in 3 methods
            >>> print(f"RRF Score: {score:.4f}")
        """
        return sum(1.0 / (self.k + rank) for rank in ranks)
