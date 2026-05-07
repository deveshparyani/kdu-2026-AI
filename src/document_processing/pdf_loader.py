"""
PDF loading module for extracting text from PDF documents.

This module provides functionality to load PDF files and extract text
with proper error handling and file size validation.
"""

import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from src.utils.logger import setup_logger, log_error_with_context, create_user_friendly_error

logger = setup_logger(__name__)


class PDFLoadError(Exception):
    """Exception raised when PDF loading fails."""
    pass


class PDFLoader:
    """
    Loads and extracts text from PDF files.
    
    This class handles PDF file loading with file size validation
    and proper error handling. It uses LangChain's PyPDFLoader
    under the hood.
    
    Attributes:
        max_size_mb: Maximum allowed PDF file size in megabytes
    """
    
    def __init__(self, max_size_mb: int = 50):
        """
        Initialize PDF loader with size limit.
        
        Args:
            max_size_mb: Maximum PDF file size in MB (default: 50)
        """
        self.max_size_mb = max_size_mb
        logger.info(f"PDFLoader initialized with max_size_mb={max_size_mb}")
    
    def load(self, file_path: str) -> List[Document]:
        """
        Load PDF and extract text from all pages.
        
        This method:
        1. Validates that the file exists
        2. Checks that the file size is within limits
        3. Extracts text from all pages
        4. Returns a list of Document objects with page metadata
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List[Document]: List of Document objects, one per page.
                           Each document contains:
                           - page_content: The text content of the page
                           - metadata: Dict with 'source' (file path) and 'page' (page number)
            
        Raises:
            ValueError: If file doesn't exist or exceeds size limit
            PDFLoadError: If text extraction fails
            
        Example:
            >>> loader = PDFLoader(max_size_mb=50)
            >>> documents = loader.load("research_paper.pdf")
            >>> print(f"Loaded {len(documents)} pages")
            >>> print(f"First page: {documents[0].page_content[:100]}...")
        """
        logger.info(f"Loading PDF from: {file_path}")
        
        # Step 1: Check if file exists
        if not os.path.exists(file_path):
            error_msg = f"PDF file not found: {file_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Step 2: Check file size
        try:
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)  # Convert bytes to MB
            
            logger.debug(f"PDF file size: {file_size_mb:.2f} MB")
            
            if file_size_mb > self.max_size_mb:
                error_msg = (
                    f"PDF file size ({file_size_mb:.2f} MB) exceeds maximum "
                    f"allowed size ({self.max_size_mb} MB)"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        except OSError as e:
            error_msg = f"Failed to check file size: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Step 3: Load PDF and extract text
        try:
            # Use LangChain's PyPDFLoader to extract text
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            logger.info(f"Successfully loaded {len(documents)} pages from PDF")
            
            # Log a sample of the first page for debugging
            if documents:
                first_page_preview = documents[0].page_content[:200]
                logger.debug(f"First page preview: {first_page_preview}...")
            
            return documents
        
        except Exception as e:
            # Log the error with context
            log_error_with_context(
                logger,
                e,
                component="PDFLoader",
                operation="load_pdf",
                file_path=file_path
            )
            
            # Create user-friendly error message
            user_msg = create_user_friendly_error(e, "loading PDF")
            raise PDFLoadError(user_msg) from e
    
    def validate_documents(self, documents: List[Document]) -> bool:
        """
        Validate that loaded documents have required structure.
        
        This method checks that:
        - Documents list is not empty
        - Each document has page_content
        - Each document has metadata with 'source' and 'page'
        
        Args:
            documents: List of Document objects to validate
            
        Returns:
            bool: True if documents are valid
            
        Raises:
            ValueError: If documents are invalid
        """
        if not documents:
            raise ValueError("No documents loaded from PDF")
        
        for i, doc in enumerate(documents):
            # Check page_content exists and is not empty
            if not hasattr(doc, 'page_content') or not doc.page_content:
                raise ValueError(f"Document {i} has no page_content")
            
            # Check metadata exists
            if not hasattr(doc, 'metadata') or not doc.metadata:
                raise ValueError(f"Document {i} has no metadata")
            
            # Check required metadata fields
            if 'source' not in doc.metadata:
                raise ValueError(f"Document {i} metadata missing 'source' field")
            
            if 'page' not in doc.metadata:
                raise ValueError(f"Document {i} metadata missing 'page' field")
        
        logger.debug(f"Validated {len(documents)} documents")
        return True
