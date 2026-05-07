"""
BM25 retrieval module for keyword-based search.

This module provides BM25 (Best Matching 25) algorithm for keyword-based
document retrieval, which is effective for exact keyword matches.
"""

from typing import List, Tuple
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BM25Retriever:
    """
    BM25 keyword-based retriever.
    
    BM25 is a ranking function used for keyword-based search.
    It's particularly good at finding documents that contain
    specific keywords from the query.
    
    Attributes:
        documents: List of documents in the corpus
        bm25: BM25Okapi instance
        tokenized_corpus: Tokenized version of documents
    """
    
    def __init__(self, documents: List[Document]):
        """
        Initialize BM25 index with documents.
        
        Args:
            documents: List of document chunks to index
        """
        logger.info(f"Initializing BM25Retriever with {len(documents)} documents")
        
        self.documents = documents
        
        # Tokenize documents (split into words)
        self.tokenized_corpus = [
            doc.page_content.lower().split()
            for doc in documents
        ]
        
        # Create BM25 index
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        
        logger.info("BM25 index created successfully")
    
    def retrieve(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """
        Retrieve top-k documents using BM25 scoring.
        
        This method:
        1. Tokenizes the query
        2. Calculates BM25 scores for all documents
        3. Returns top-k documents with highest scores
        
        Args:
            query: Search query
            k: Number of results to return (default: 5)
            
        Returns:
            List[Tuple[Document, float]]: List of (document, bm25_score) tuples.
                                         Scores are non-negative (higher is better).
                                         Results are sorted by score (highest first).
            
        Example:
            >>> retriever = BM25Retriever(documents)
            >>> results = retriever.retrieve("machine learning algorithms", k=3)
            >>> for doc, score in results:
            ...     print(f"Score: {score:.2f}, Text: {doc.page_content[:100]}...")
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to BM25 retrieve")
            return []
        
        logger.debug(f"BM25 retrieval for query: '{query[:100]}...'")
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k document indices
        top_k_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:k]
        
        # Create results list
        results = [
            (self.documents[i], float(scores[i]))
            for i in top_k_indices
        ]
        
        logger.info(f"BM25 retrieval returned {len(results)} results")
        
        if results:
            logger.debug(f"Top BM25 score: {results[0][1]:.2f}")
        
        return results
    
    def update_documents(self, documents: List[Document]) -> None:
        """
        Update the BM25 index with new documents.
        
        This replaces the existing index with a new one.
        
        Args:
            documents: New list of documents to index
        """
        logger.info(f"Updating BM25 index with {len(documents)} documents")
        
        self.documents = documents
        self.tokenized_corpus = [
            doc.page_content.lower().split()
            for doc in documents
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        
        logger.info("BM25 index updated successfully")
