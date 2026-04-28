"""Text normalization and chunking."""

import re
import uuid

import tiktoken

from ..config import Config
from ..models import ProcessingState, TextChunk


def normalize_text(state: ProcessingState) -> ProcessingState:
    """Clean and chunk text for embedding and summarization.
    
    Args:
        state: ProcessingState with raw_text set
        
    Returns:
        Updated ProcessingState with chunks populated
    """
    try:
        # Clean the text
        cleaned_text = _clean_text(state.raw_text)
        
        # Chunk the text
        chunks = _chunk_by_tokens(
            text=cleaned_text,
            max_tokens=Config.MAX_CHUNK_TOKENS,
            overlap=Config.CHUNK_OVERLAP_TOKENS,
            source_file=state.file_id
        )
        
        state.chunks = chunks
        return state
        
    except Exception as e:
        state.error = f"Text normalization failed: {str(e)}"
        return state


def _clean_text(text: str) -> str:
    """Clean text by removing excessive whitespace and control characters."""
    if not text:
        return ""
    
    # Remove control characters except newline and tab
    cleaned = "".join(char for char in text if ord(char) >= 32 or char in ['\n', '\t'])
    
    # Normalize whitespace
    cleaned = re.sub(r' +', ' ', cleaned)  # Multiple spaces to one
    cleaned = re.sub(r'\n\n\n+', '\n\n', cleaned)  # Max 2 newlines
    
    return cleaned.strip()


def _chunk_by_tokens(
    text: str,
    max_tokens: int,
    overlap: int,
    source_file: str
) -> list[TextChunk]:
    """Chunk text by token count with overlap."""
    # Initialize tokenizer
    encoding = tiktoken.get_encoding("cl100k_base")
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = len(encoding.encode(sentence))
        
        if current_tokens + sentence_tokens > max_tokens and current_chunk:
            # Create chunk
            chunk_text = " ".join(current_chunk)
            chunk = TextChunk(
                chunk_id=str(uuid.uuid4()),
                text=chunk_text,
                source_file=source_file,
                page_or_timestamp=None,
                token_count=current_tokens
            )
            chunks.append(chunk)
            
            # Start new chunk with overlap
            overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
            current_chunk = overlap_sentences + [sentence]
            current_tokens = len(encoding.encode(" ".join(current_chunk)))
        else:
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
    
    # Add final chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunk = TextChunk(
            chunk_id=str(uuid.uuid4()),
            text=chunk_text,
            source_file=source_file,
            page_or_timestamp=None,
            token_count=len(encoding.encode(chunk_text))
        )
        chunks.append(chunk)
    
    return chunks
