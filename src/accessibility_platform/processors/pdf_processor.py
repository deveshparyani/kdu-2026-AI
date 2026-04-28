"""PDF processing module.

This module handles PDF file processing, including:
- Text extraction from text-based PDFs
- Detection of image-only pages (for future vision API integration)
- Cross-page context preservation
"""

import pymupdf  # PyMuPDF

from ..config import Config
from ..cost_tracker import CostTracker
from ..models import ProcessingState


def process_pdf(
    state: ProcessingState,
    openai_client=None,  # Will be used in Step 6 for vision API
    cost_tracker: CostTracker = None
) -> ProcessingState:
    """Process a PDF file and extract text.
    
    This function:
    1. Opens the PDF file
    2. Extracts text from each page
    3. Combines all page texts (preserves cross-page context)
    4. Handles empty PDFs gracefully
    
    In Step 6, we'll add:
    - Detection of image-only pages
    - Vision API calls for images
    - Embedded image extraction
    
    Args:
        state: ProcessingState object with file_path set
        openai_client: OpenAI client (not used in Step 5, needed for Step 6)
        cost_tracker: CostTracker instance (not used in Step 5, needed for Step 6)
        
    Returns:
        Updated ProcessingState with raw_text populated
        
    Raises:
        Exception: If PDF processing fails (error stored in state.error)
    """
    try:
        # Open the PDF file
        doc = pymupdf.open(state.file_path)
        
        # Check if PDF is empty
        if len(doc) == 0:
            state.error = "PDF file is empty (0 pages)"
            return state
        
        # Extract text from all pages
        all_text = []
        
        for page_num in range(len(doc)):
            # Get the page
            page = doc[page_num]
            
            # Extract text from the page
            page_text = page.get_text()
            
            # Clean up the text (remove excessive whitespace)
            page_text = _clean_text(page_text)
            
            # Add page marker for context (helps with debugging)
            # Format: [Page X] followed by the text
            if page_text.strip():  # Only add if page has text
                page_marker = f"[Page {page_num + 1}]\n"
                all_text.append(page_marker + page_text)
        
        # Close the document
        doc.close()
        
        # Combine all page texts with double newline separator
        # This preserves cross-page context while maintaining readability
        state.raw_text = "\n\n".join(all_text)
        
        # Handle case where PDF has pages but no extractable text
        if not state.raw_text.strip():
            state.error = (
                "PDF contains no extractable text. "
                "This may be a scanned document or image-based PDF. "
                "Vision API support will be added in Step 6."
            )
        
        return state
        
    except Exception as e:
        # Store error in state instead of raising
        # This allows the pipeline to handle errors gracefully
        state.error = f"PDF processing failed: {str(e)}"
        return state


def _clean_text(text: str) -> str:
    """Clean extracted text by removing excessive whitespace.
    
    This function:
    - Removes control characters (except newlines and tabs)
    - Collapses multiple spaces into one
    - Removes excessive blank lines (more than 2 consecutive)
    - Strips leading/trailing whitespace
    
    Args:
        text: Raw text extracted from PDF
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove control characters except newline and tab
    # Control characters are in the range 0x00-0x1F except \n (0x0A) and \t (0x09)
    cleaned = ""
    for char in text:
        char_code = ord(char)
        if char_code >= 32 or char in ['\n', '\t']:
            cleaned += char
    
    # Replace multiple spaces with single space
    # But preserve newlines
    lines = cleaned.split('\n')
    cleaned_lines = []
    for line in lines:
        # Collapse multiple spaces in each line
        line = ' '.join(line.split())
        cleaned_lines.append(line)
    
    # Join lines back together
    cleaned = '\n'.join(cleaned_lines)
    
    # Remove excessive blank lines (more than 2 consecutive)
    while '\n\n\n' in cleaned:
        cleaned = cleaned.replace('\n\n\n', '\n\n')
    
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned


def get_pdf_info(file_path: str) -> dict:
    """Get metadata about a PDF file.
    
    This is a utility function that returns PDF metadata without processing
    the entire document. Useful for debugging and logging.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Dictionary with PDF information:
        - page_count: Number of pages
        - has_text: Whether PDF contains extractable text
        - metadata: PDF metadata (title, author, etc.)
        
    Raises:
        Exception: If PDF cannot be opened
    """
    doc = pymupdf.open(file_path)
    
    # Get page count
    page_count = len(doc)
    
    # Check if PDF has extractable text (sample first page)
    has_text = False
    if page_count > 0:
        first_page_text = doc[0].get_text().strip()
        has_text = len(first_page_text) > 0
    
    # Get metadata
    metadata = doc.metadata
    
    doc.close()
    
    return {
        "page_count": page_count,
        "has_text": has_text,
        "metadata": {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
        }
    }


# ============================================================================
# Future Enhancements (Step 6)
# ============================================================================

# In Step 6, we'll add these functions:
# - _detect_image_only_pages(doc) -> List[int]
# - _extract_embedded_images(page) -> List[bytes]
# - _process_page_with_vision(page, openai_client, cost_tracker) -> str
# - _insert_image_descriptions(text, descriptions) -> str

# These will enable:
# - Detection of scanned/image-only pages
# - Vision API calls for image description
# - Embedded image extraction and processing
# - Inline insertion of image descriptions
