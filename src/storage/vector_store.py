"""
Vector storage module using ChromaDB for semantic search.

This module provides functionality to store document chunks with embeddings
and perform similarity-based retrieval.
"""

from typing import List, Tuple
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.utils.logger import setup_logger, log_error_with_context

logger = setup_logger(__name__)


class VectorStore:
    """
    ChromaDB wrapper for vector storage and retrieval.
    
    This class handles:
    - Storing document chunks with embeddings
    - Generating embeddings using sentence-transformers
    - Performing semantic similarity search
    - Graceful error handling for embedding failures
    
    Attributes:
        collection_name: Name of the ChromaDB collection
        embedding_model: Name of the sentence-transformers model
        embeddings: HuggingFaceEmbeddings instance
        vectorstore: Chroma vectorstore instance
    """
    
    def __init__(
        self,
        collection_name: str = "hybrid_graphrag",
        embedding_model: str = "all-MiniLM-L6-v2",
        persist_directory: str = "./chroma_db"
    ):
        """
        Initialize ChromaDB collection.
        
        This creates a new collection or connects to an existing one.
        The embedding model is downloaded automatically on first use.
        
        Args:
            collection_name: Name of ChromaDB collection (default: "hybrid_graphrag")
            embedding_model: sentence-transformers model name 
                           (default: "all-MiniLM-L6-v2" - fast and lightweight)
            persist_directory: Directory to store ChromaDB data (default: "./chroma_db")
        """
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        logger.info(
            f"Initializing VectorStore with collection='{collection_name}', "
            f"embedding_model='{embedding_model}'"
        )
        
        try:
            # Initialize embeddings model
            # This will download the model on first use (cached afterwards)
            self.embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model,
                model_kwargs={'device': 'cpu'},  # Use CPU (change to 'cuda' for GPU)
                encode_kwargs={'normalize_embeddings': True}  # Normalize for cosine similarity
            )
            
            logger.info(f"Embedding model '{embedding_model}' loaded successfully")
            
            # Initialize ChromaDB vectorstore
            # This creates the collection if it doesn't exist
            self.vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=persist_directory
            )
            
            logger.info(f"ChromaDB collection '{collection_name}' initialized")
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="VectorStore",
                operation="initialization",
                collection_name=collection_name,
                embedding_model=embedding_model
            )
            raise
    
    def add_documents(self, chunks: List[Document]) -> None:
        """
        Add document chunks with embeddings to ChromaDB.
        
        This method:
        1. Generates embeddings for each chunk using sentence-transformers
        2. Stores chunks and embeddings in ChromaDB
        3. Handles errors gracefully (logs and skips failed chunks)
        
        Args:
            chunks: List of document chunks to store
            
        Example:
            >>> vector_store = VectorStore()
            >>> chunks = [Document(page_content="text", metadata={"chunk_id": "123"})]
            >>> vector_store.add_documents(chunks)
            Successfully added 1 documents to vector store
        """
        if not chunks:
            logger.warning("No chunks provided to add_documents")
            return
        
        logger.info(f"Adding {len(chunks)} documents to vector store")
        
        successful_chunks = []
        failed_chunks = 0
        
        # Process chunks in batches to handle errors gracefully
        for i, chunk in enumerate(chunks):
            try:
                # Validate chunk has content
                if not chunk.page_content or not chunk.page_content.strip():
                    logger.warning(f"Skipping empty chunk at index {i}")
                    failed_chunks += 1
                    continue
                
                successful_chunks.append(chunk)
            
            except Exception as e:
                log_error_with_context(
                    logger,
                    e,
                    component="VectorStore",
                    operation="validate_chunk",
                    chunk_index=i
                )
                failed_chunks += 1
        
        # Add all successful chunks to vectorstore
        if successful_chunks:
            try:
                self.vectorstore.add_documents(successful_chunks)
                logger.info(
                    f"Successfully added {len(successful_chunks)} documents to vector store"
                )
            except Exception as e:
                log_error_with_context(
                    logger,
                    e,
                    component="VectorStore",
                    operation="add_documents",
                    num_chunks=len(successful_chunks)
                )
                raise
        
        if failed_chunks > 0:
            logger.warning(
                f"Failed to process {failed_chunks} chunks (skipped empty or invalid chunks)"
            )
    
    def similarity_search(
        self,
        query: str,
        k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Perform semantic similarity search.
        
        This method:
        1. Generates embedding for the query
        2. Finds top-k most similar chunks using cosine similarity
        3. Returns chunks with their similarity scores
        
        Args:
            query: Search query text
            k: Number of results to return (default: 5)
            
        Returns:
            List[Tuple[Document, float]]: List of (document, similarity_score) tuples.
                                         Scores are between 0 and 1 (higher is more similar).
                                         Results are sorted by score (highest first).
            
        Example:
            >>> vector_store = VectorStore()
            >>> results = vector_store.similarity_search("What is machine learning?", k=3)
            >>> for doc, score in results:
            ...     print(f"Score: {score:.3f}, Text: {doc.page_content[:100]}...")
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to similarity_search")
            return []
        
        logger.debug(f"Performing similarity search for query: '{query[:100]}...'")
        
        try:
            # Perform similarity search with scores
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            logger.info(f"Found {len(results)} results for similarity search")
            
            # Log top result for debugging
            if results:
                top_doc, top_score = results[0]
                logger.debug(
                    f"Top result score: {top_score:.3f}, "
                    f"preview: {top_doc.page_content[:100]}..."
                )
            
            return results
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="VectorStore",
                operation="similarity_search",
                query_length=len(query),
                k=k
            )
            # Return empty results on error (graceful degradation)
            return []
    
    def get_all_documents(self) -> List[Document]:
        """
        Get all documents from the vector store.
        
        This is useful for initializing other retrievers (like BM25)
        that need access to the full document corpus.
        
        Returns:
            List[Document]: All documents in the vector store
        """
        try:
            # Get all documents from the collection
            collection = self.vectorstore._collection
            results = collection.get()
            
            # Convert to Document objects
            documents = []
            for i in range(len(results['ids'])):
                doc = Document(
                    page_content=results['documents'][i],
                    metadata=results['metadatas'][i] if results['metadatas'] else {}
                )
                documents.append(doc)
            
            logger.info(f"Retrieved {len(documents)} documents from vector store")
            return documents
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="VectorStore",
                operation="get_all_documents"
            )
            return []
    
    def clear(self) -> None:
        """
        Clear all documents from the vector store.
        
        Warning: This permanently deletes all stored documents and embeddings.
        """
        try:
            # Delete the collection and recreate it
            self.vectorstore._client.delete_collection(self.collection_name)
            
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.vectorstore._persist_directory
            )
            
            logger.info(f"Cleared vector store collection '{self.collection_name}'")
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="VectorStore",
                operation="clear"
            )
            raise
