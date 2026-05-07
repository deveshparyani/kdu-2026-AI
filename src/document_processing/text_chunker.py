"""
Text chunking module for splitting documents into smaller chunks.

This module provides functionality to chunk documents using
RecursiveCharacterTextSplitter while preserving metadata.
"""

from typing import List
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class TextChunker:
    """
    Chunks text using RecursiveCharacterTextSplitter.
    
    This class splits long documents into smaller chunks while:
    - Maintaining semantic coherence (tries to split at natural boundaries)
    - Preserving metadata from original documents
    - Adding unique chunk IDs for tracking
    - Allowing overlap between chunks for context preservation
    
    Attributes:
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        splitter: RecursiveCharacterTextSplitter instance
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize chunker with configuration.
        
        The RecursiveCharacterTextSplitter tries to split text at natural
        boundaries in this order:
        1. Double newlines (paragraphs)
        2. Single newlines (lines)
        3. Spaces (words)
        4. Characters (as last resort)
        
        Args:
            chunk_size: Target size of each chunk in characters (default: 1000)
            chunk_overlap: Overlap between consecutive chunks (default: 200)
                          This helps maintain context across chunk boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Create the text splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,  # Use character count
            separators=["\n\n", "\n", " ", ""],  # Try these separators in order
        )
        
        logger.info(
            f"TextChunker initialized with chunk_size={chunk_size}, "
            f"chunk_overlap={chunk_overlap}"
        )
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks with metadata preservation.
        
        This method:
        1. Splits each document into smaller chunks
        2. Preserves original metadata (source, page)
        3. Adds a unique chunk_id to each chunk
        4. Adds chunk_index to track position within original document
        
        Args:
            documents: List of Document objects to chunk
            
        Returns:
            List[Document]: List of chunked Document objects.
                           Each chunk has metadata:
                           - source: Original file path
                           - page: Page number in original document
                           - chunk_id: Unique identifier for this chunk
                           - chunk_index: Position of chunk within original document
            
        Example:
            >>> chunker = TextChunker(chunk_size=500, chunk_overlap=50)
            >>> documents = [Document(page_content="Long text...", metadata={"source": "file.pdf", "page": 0})]
            >>> chunks = chunker.chunk_documents(documents)
            >>> print(f"Created {len(chunks)} chunks from {len(documents)} documents")
            >>> print(f"First chunk ID: {chunks[0].metadata['chunk_id']}")
        """
        logger.info(f"Chunking {len(documents)} documents")
        
        all_chunks = []
        total_original_chars = 0
        total_chunk_chars = 0
        
        # Process each document
        for doc_index, document in enumerate(documents):
            # Track original document size
            original_size = len(document.page_content)
            total_original_chars += original_size
            
            # Split the document into chunks
            chunks = self.splitter.split_documents([document])
            
            logger.debug(
                f"Document {doc_index} ({original_size} chars) split into {len(chunks)} chunks"
            )
            
            # Add chunk-specific metadata to each chunk
            for chunk_index, chunk in enumerate(chunks):
                # Generate unique chunk ID
                chunk_id = str(uuid.uuid4())
                
                # Preserve original metadata and add chunk-specific fields
                chunk.metadata.update({
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "total_chunks": len(chunks),
                })
                
                # Track chunk size
                total_chunk_chars += len(chunk.page_content)
                
                all_chunks.append(chunk)
        
        # Log statistics
        logger.info(
            f"Chunking complete: {len(documents)} documents -> {len(all_chunks)} chunks"
        )
        logger.debug(
            f"Total characters: {total_original_chars} original, "
            f"{total_chunk_chars} in chunks (includes overlap)"
        )
        
        # Calculate average chunk size
        if all_chunks:
            avg_chunk_size = total_chunk_chars / len(all_chunks)
            logger.debug(f"Average chunk size: {avg_chunk_size:.0f} characters")
        
        return all_chunks
    
    def chunk_text(self, text: str, metadata: dict = None) -> List[Document]:
        """
        Chunk a single text string into documents.
        
        This is a convenience method for chunking raw text without
        first creating a Document object.
        
        Args:
            text: Text string to chunk
            metadata: Optional metadata to attach to all chunks
            
        Returns:
            List[Document]: List of chunked Document objects
            
        Example:
            >>> chunker = TextChunker()
            >>> text = "Very long text content..."
            >>> chunks = chunker.chunk_text(text, metadata={"source": "manual_input"})
        """
        # Create a document from the text
        if metadata is None:
            metadata = {}
        
        document = Document(page_content=text, metadata=metadata)
        
        # Chunk the document
        return self.chunk_documents([document])
    
    def get_chunk_stats(self, chunks: List[Document]) -> dict:
        """
        Get statistics about chunked documents.
        
        Args:
            chunks: List of chunked documents
            
        Returns:
            dict: Statistics including:
                - total_chunks: Number of chunks
                - total_chars: Total characters across all chunks
                - avg_chunk_size: Average chunk size in characters
                - min_chunk_size: Smallest chunk size
                - max_chunk_size: Largest chunk size
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "total_chars": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
            }
        
        chunk_sizes = [len(chunk.page_content) for chunk in chunks]
        total_chars = sum(chunk_sizes)
        
        stats = {
            "total_chunks": len(chunks),
            "total_chars": total_chars,
            "avg_chunk_size": total_chars / len(chunks),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
        }
        
        return stats
