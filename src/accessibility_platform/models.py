"""Data models for the accessibility platform.

This module defines all the data structures used throughout the application.
We use dataclasses for mutable objects and TypedDict for dictionary-like structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict



@dataclass
class CostEntry:
    """Represents a single API call and its associated cost.
    
    This is used to track every API call we make (vision, embeddings, summarization)
    so we can calculate the total cost and provide breakdowns to users.
    
    Attributes:
        model: Name of the AI model used (e.g., "gpt-4o-mini")
        operation: Type of operation (e.g., "vision", "embedding", "summarization")
        prompt_tokens: Number of input tokens sent to the API
        completion_tokens: Number of output tokens received from the API
        cost_usd: Calculated cost in US dollars
        file_id: ID of the file being processed
        timestamp: When this API call was made (ISO 8601 format)
    """
    model: str
    operation: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    file_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def __post_init__(self) -> None:
        """Validate the cost entry after initialization."""
        # Ensure cost is non-negative
        if self.cost_usd < 0:
            raise ValueError(f"Cost cannot be negative: {self.cost_usd}")
        
        # Ensure token counts are non-negative
        if self.prompt_tokens < 0 or self.completion_tokens < 0:
            raise ValueError("Token counts cannot be negative")


class CostSummary(TypedDict):
    """Summary of costs for one or more files.
    
    This provides an aggregated view of all costs, broken down by operation
    and model type.
    
    Attributes:
        file_id: ID of the file (None means all files)
        total_cost_usd: Total cost across all operations
        by_operation: Cost breakdown by operation type
        by_model: Cost breakdown by model name
        total_tokens: Total number of tokens processed
    """
    file_id: str | None
    total_cost_usd: float
    by_operation: dict[str, float]  # e.g., {"vision": 0.002, "embedding": 0.0001}
    by_model: dict[str, float]      
    total_tokens: int



@dataclass
class TextChunk:
    """Represents a chunk of text extracted from a document.
    
    Documents are split into chunks for embedding and retrieval. Each chunk
    contains a portion of the text along with metadata about its source.
    
    Attributes:
        chunk_id: Unique identifier for this chunk
        text: The actual text content
        source_file: Name of the source file
        page_or_timestamp: Page number (for PDFs) or timestamp (for audio)
        token_count: Number of tokens in this chunk
    """
    chunk_id: str
    text: str
    source_file: str
    page_or_timestamp: str | None
    token_count: int
    
    def __post_init__(self) -> None:
        """Validate the text chunk after initialization."""
        # Ensure text is not empty
        if not self.text.strip():
            raise ValueError("Text chunk cannot be empty")
        
        # Ensure token count is positive
        if self.token_count <= 0:
            raise ValueError(f"Token count must be positive: {self.token_count}")


@dataclass
class ProcessingState:
    """Represents the state of a file as it moves through the processing pipeline.
    
    This object is passed between different processing functions (PDF processor,
    normalizer, summarizer, etc.) and accumulates data at each step.
    
    Attributes:
        file_path: Path to the uploaded file
        file_id: Unique identifier for this file
        file_type: Type of file ("pdf", "image", or "audio")
        raw_text: Extracted text from the file
        chunks: List of text chunks created from raw_text
        summary: AI-generated summary of the content
        key_points: List of 5-7 key points from the content
        tags: List of topic tags
        embedding_ids: IDs of embeddings stored in vector database
        error: Error message if processing failed (None if successful)
    """
    file_path: str
    file_id: str
    file_type: str
    raw_text: str = ""
    chunks: list[TextChunk] = field(default_factory=list)
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    embedding_ids: list[str] = field(default_factory=list)
    error: str | None = None
    
    def __post_init__(self) -> None:
        """Validate the processing state after initialization."""
        # Validate file type
        valid_types = {"pdf", "image", "audio"}
        if self.file_type not in valid_types:
            raise ValueError(
                f"Invalid file_type: {self.file_type}. "
                f"Must be one of {valid_types}"
            )
    
    def has_error(self) -> bool:
        """Check if processing encountered an error.
        
        Returns:
            True if there was an error, False otherwise
        """
        return self.error is not None
    
    def is_processed(self) -> bool:
        """Check if the file has been fully processed.
        
        Returns:
            True if processing is complete (has chunks and embeddings)
        """
        return len(self.chunks) > 0 and len(self.embedding_ids) > 0



class AccessibilityResult(TypedDict):
    """Final result returned to the user after processing a file.
    
    This contains everything the user needs: the extracted text, AI-generated
    summary and key points, cost information, and processing time.
    
    Attributes:
        file_id: Unique identifier for the file
        file_name: Original name of the uploaded file
        transcript: Full extracted text
        summary: AI-generated summary (150 words)
        key_points: List of 5-7 key bullet points
        tags: List of topic tags
        cost_summary: Breakdown of API costs
        processing_time_seconds: How long processing took
    """
    file_id: str
    file_name: str
    transcript: str
    summary: str
    key_points: list[str]
    tags: list[str]
    cost_summary: CostSummary
    processing_time_seconds: float


class SearchResult(TypedDict):
    """Represents a single search result from the vector database.
    
    When a user searches for content, we return a list of these results,
    ranked by relevance.
    
    Attributes:
        chunk_id: ID of the matching text chunk
        text: The actual text content
        source_file: Name of the source file
        page_or_timestamp: Page number or timestamp where this text appears
        similarity_score: How relevant this result is (0.0 to 1.0)
        context_window: Surrounding text for additional context
    """
    chunk_id: str
    text: str
    source_file: str
    page_or_timestamp: str | None
    similarity_score: float
    context_window: str



def validate_key_points(key_points: list[str]) -> None:
    """Validate that key points list meets requirements.
    
    Args:
        key_points: List of key points to validate
        
    Raises:
        ValueError: If key points don't meet requirements (must be 5-7 items)
    """
    if not (5 <= len(key_points) <= 7):
        raise ValueError(
            f"Key points must contain 5-7 items, got {len(key_points)}"
        )


def validate_summary(summary: str, max_words: int = 200) -> None:
    """Validate that summary meets word count requirements.
    
    Args:
        summary: Summary text to validate
        max_words: Maximum number of words allowed
        
    Raises:
        ValueError: If summary exceeds word limit
    """
    word_count = len(summary.split())
    if word_count > max_words:
        raise ValueError(
            f"Summary exceeds {max_words} words: {word_count} words"
        )


def validate_similarity_score(score: float) -> None:
    """Validate that similarity score is in valid range.
    
    Args:
        score: Similarity score to validate
        
    Raises:
        ValueError: If score is not between 0.0 and 1.0
    """
    if not (0.0 <= score <= 1.0):
        raise ValueError(
            f"Similarity score must be between 0.0 and 1.0, got {score}"
        )
