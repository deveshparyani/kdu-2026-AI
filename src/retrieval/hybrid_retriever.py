"""
Hybrid retrieval module combining BM25, semantic, and graph search.

This module orchestrates three different retrieval methods and combines
their results for comprehensive document retrieval.
"""

from typing import List, Tuple, Dict
from langchain_core.documents import Document

from src.retrieval.bm25_retriever import BM25Retriever
from src.storage.vector_store import VectorStore
from src.retrieval.cypher_generator import CypherGenerator
from src.storage.graph_store import GraphStore
from src.utils.logger import setup_logger, log_error_with_context

logger = setup_logger(__name__)


class HybridRetriever:
    """
    Combines BM25, semantic, and graph retrieval.
    
    This class:
    - Executes three retrieval methods in parallel
    - Handles failures gracefully (continues with available results)
    - Tags results with source method
    - Collects all results for reranking
    
    Attributes:
        bm25_retriever: BM25 retriever instance
        vector_store: Vector store instance
        cypher_generator: Cypher generator instance
        graph_store: Graph store instance
    """
    
    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_store: VectorStore,
        cypher_generator: CypherGenerator,
        graph_store: GraphStore
    ):
        """
        Initialize with all retrieval components.
        
        Args:
            bm25_retriever: BM25 retriever instance
            vector_store: Vector store instance
            cypher_generator: Cypher generator instance
            graph_store: Graph store instance
        """
        self.bm25_retriever = bm25_retriever
        self.vector_store = vector_store
        self.cypher_generator = cypher_generator
        self.graph_store = graph_store
        
        logger.info("HybridRetriever initialized with all retrieval methods")
    
    def retrieve(
        self,
        query: str,
        k: int = 5
    ) -> Dict[str, List[Tuple[Document, float]]]:
        """
        Execute hybrid retrieval across all methods.
        
        This method:
        1. Executes BM25 keyword search
        2. Executes semantic vector search
        3. Executes graph search (generates Cypher and queries Neo4j)
        4. Collects results from all methods
        5. Handles failures gracefully (continues with available results)
        
        Args:
            query: Search query
            k: Number of results per method (default: 5)
            
        Returns:
            Dict[str, List[Tuple[Document, float]]]: Dictionary mapping method name
                                                     to list of (Document, score) tuples.
                                                     Keys: "bm25", "semantic", "graph"
            
        Example:
            >>> retriever = HybridRetriever(...)
            >>> results = retriever.retrieve("What is machine learning?", k=3)
            >>> print(f"BM25: {len(results['bm25'])} results")
            >>> print(f"Semantic: {len(results['semantic'])} results")
            >>> print(f"Graph: {len(results['graph'])} results")
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to hybrid retrieve")
            return {"bm25": [], "semantic": [], "graph": []}
        
        logger.info(f"Hybrid retrieval for query: '{query[:100]}...'")
        
        results = {
            "bm25": [],
            "semantic": [],
            "graph": []
        }
        
        # Method 1: BM25 keyword search
        try:
            logger.debug("Executing BM25 retrieval")
            bm25_results = self.bm25_retriever.retrieve(query, k=k)
            results["bm25"] = bm25_results
            logger.info(f"BM25 retrieval: {len(bm25_results)} results")
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="HybridRetriever",
                operation="bm25_retrieval",
                query=query[:100]
            )
            logger.warning("BM25 retrieval failed, continuing with other methods")
        
        # Method 2: Semantic vector search
        try:
            logger.debug("Executing semantic retrieval")
            semantic_results = self.vector_store.similarity_search(query, k=k)
            results["semantic"] = semantic_results
            logger.info(f"Semantic retrieval: {len(semantic_results)} results")
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="HybridRetriever",
                operation="semantic_retrieval",
                query=query[:100]
            )
            logger.warning("Semantic retrieval failed, continuing with other methods")
        
        # Method 3: Graph search (Cypher query)
        try:
            logger.debug("Executing graph retrieval")
            
            # Generate Cypher query
            cypher_query = self.cypher_generator.generate_cypher(query)
            
            if cypher_query:
                logger.debug(f"Generated Cypher: {cypher_query}")
                
                # Execute Cypher query
                graph_results_raw = self.graph_store.execute_cypher(cypher_query)
                
                # Convert graph results to Document format
                graph_results = self._convert_graph_results(graph_results_raw, query)
                results["graph"] = graph_results
                logger.info(f"Graph retrieval: {len(graph_results)} results")
            else:
                logger.warning("Cypher generation failed, skipping graph retrieval")
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="HybridRetriever",
                operation="graph_retrieval",
                query=query[:100]
            )
            logger.warning("Graph retrieval failed, continuing with other methods")
        
        # Log summary
        total_results = sum(len(r) for r in results.values())
        logger.info(
            f"Hybrid retrieval complete: {total_results} total results "
            f"(BM25: {len(results['bm25'])}, Semantic: {len(results['semantic'])}, "
            f"Graph: {len(results['graph'])})"
        )
        
        return results
    
    def _convert_graph_results(
        self,
        graph_results: List[Dict],
        query: str
    ) -> List[Tuple[Document, float]]:
        """
        Convert graph query results to Document format.
        
        This method extracts text content from graph results and
        creates Document objects for reranking.
        
        Args:
            graph_results: Raw results from Neo4j Cypher query
            query: Original query (for scoring)
            
        Returns:
            List[Tuple[Document, float]]: List of (Document, score) tuples
        """
        documents = []
        
        for i, result in enumerate(graph_results):
            try:
                # Extract text content from result
                # Results can contain nodes, relationships, paths, or properties
                content_parts = []
                
                for key, value in result.items():
                    if value is not None:
                        # Convert value to string representation
                        content_parts.append(f"{key}: {str(value)}")
                
                if content_parts:
                    content = "\n".join(content_parts)
                    
                    # Create Document
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": "graph",
                            "query": query,
                            "result_index": i
                        }
                    )
                    
                    # Assign score (higher rank = lower score)
                    score = 1.0 / (i + 1)
                    
                    documents.append((doc, score))
            
            except Exception as e:
                log_error_with_context(
                    logger,
                    e,
                    component="HybridRetriever",
                    operation="convert_graph_result",
                    result_index=i
                )
                continue
        
        return documents
