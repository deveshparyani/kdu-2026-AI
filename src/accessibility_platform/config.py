"""Configuration module for the accessibility platform.

This module loads environment variables and defines constants used throughout the application.
"""

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class that holds all application settings."""
    
    
    # OpenAI API key (required)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # OpenRouter API key (optional fallback)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    
    
    # Maximum file size in megabytes
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    
    # Maximum file size in bytes (calculated from MB)
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    
    
    # Maximum number of file uploads per user per minute
    MAX_UPLOADS_PER_MINUTE: int = int(os.getenv("MAX_UPLOADS_PER_MINUTE", "10"))
    
    # Maximum number of searches per user per minute
    MAX_SEARCHES_PER_MINUTE: int = int(os.getenv("MAX_SEARCHES_PER_MINUTE", "50"))
    
    
    # Cache time-to-live in seconds (default: 1 hour)
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    
    
    # Path to ChromaDB persistence directory
    CHROMA_PERSIST_DIRECTORY: str = os.getenv(
        "CHROMA_PERSIST_DIRECTORY", 
        "./data/chroma_db"
    )
    
    # Path to SQLite database file
    SQLITE_DB_PATH: str = os.getenv(
        "SQLITE_DB_PATH", 
        "./data/accessibility.db"
    )
    
    
    # Whisper model size: tiny, base, small, medium, large
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base")
    
    # Whether to use cross-encoder re-ranking for search
    USE_CROSS_ENCODER_RERANKING: bool = os.getenv(
        "USE_CROSS_ENCODER_RERANKING", 
        "true"
    ).lower() == "true"
    
    # Cross-encoder model name
    CROSS_ENCODER_MODEL: str = os.getenv(
        "CROSS_ENCODER_MODEL",
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    
    
    # Maximum tokens per chunk for embedding
    MAX_CHUNK_TOKENS: int = 500
    
    # Token overlap between consecutive chunks
    CHUNK_OVERLAP_TOKENS: int = 50
    
    # Maximum tokens to send to summarizer
    MAX_SUMMARY_INPUT_TOKENS: int = 3000
    
    # Minimum text length to consider a PDF page as having text (not image-only)
    MIN_PAGE_TEXT_LENGTH: int = 50
    
    # Minimum image size in bytes to process with vision API (filters out icons)
    MIN_IMAGE_SIZE_BYTES: int = 10 * 1024  # 10 KB
    
    
    # Pricing table for cost calculation
    # Format: {model_name: {input_per_1k: price, output_per_1k: price}}
    PRICING: Dict[str, Dict[str, float]] = {
        "gpt-4o-mini": {
            "input_per_1k": 0.000150,   # $0.15 per 1M input tokens
            "output_per_1k": 0.000600,  # $0.60 per 1M output tokens
        },
        "text-embedding-3-small": {
            "input_per_1k": 0.000020,   # $0.02 per 1M tokens
            "output_per_1k": 0.0,       # No output tokens for embeddings
        },
    }
    
    
    # Supported file extensions and their corresponding MIME types
    # This is used for security validation (extension must match MIME type)
    VALID_FILE_TYPES: Dict[str, str] = {
        # PDF files
        ".pdf": "application/pdf",
        
        # Image files
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        
        # Audio files
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
    }
    
    
    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    
    @classmethod
    def validate(cls) -> None:
        """Validate that required configuration is present.
        
        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        # Check if OpenAI API key is set
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file."
            )
        
        # Check if API key looks valid (starts with 'sk-')
        if not cls.OPENAI_API_KEY.startswith("sk-"):
            raise ValueError(
                "OPENAI_API_KEY appears to be invalid. "
                "OpenAI API keys should start with 'sk-'"
            )
        
        # Create data directories if they don't exist
        Path(cls.CHROMA_PERSIST_DIRECTORY).mkdir(parents=True, exist_ok=True)
        Path(cls.SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """Get list of supported file extensions.
        
        Returns:
            List of supported file extensions (e.g., ['.pdf', '.jpg', ...])
        """
        return list(cls.VALID_FILE_TYPES.keys())
    
    @classmethod
    def get_mime_type(cls, extension: str) -> str | None:
        """Get the expected MIME type for a file extension.
        
        Args:
            extension: File extension (e.g., '.pdf')
            
        Returns:
            Expected MIME type or None if extension not supported
        """
        return cls.VALID_FILE_TYPES.get(extension.lower())


# Validate configuration on module import
Config.validate()
