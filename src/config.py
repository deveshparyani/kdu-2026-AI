"""
Configuration management for the Hybrid GraphRAG Chatbot.

This module handles loading configuration from environment variables
and provides default values for all optional parameters.
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """
    System configuration for the Hybrid GraphRAG Chatbot.
    
    This class holds all configuration parameters needed by the system,
    including API keys, database credentials, and tuning parameters.
    """
    
    # Required fields (no defaults)
    openai_api_key: str
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str
    
    # Optional fields (with defaults)
    openai_model: str = "gpt-4.1-nano"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_results: int = 5
    rrf_constant: int = 60
    entity_similarity_threshold: float = 0.85
    embedding_model: str = "all-MiniLM-L6-v2"
    answer_timeout: int = 30
    multi_hop_timeout: int = 45
    max_pdf_size_mb: int = 50
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.
        
        This method reads configuration from environment variables and provides
        default values for optional parameters. It also validates that required
        fields are present and have valid values.
        
        Returns:
            Config: Configuration object with all parameters set
            
        Raises:
            ValueError: If required environment variables are missing or invalid
        """
        # Get required environment variables
        openai_api_key = os.getenv("OPENAI_API_KEY")
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_username = os.getenv("NEO4J_USERNAME")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        neo4j_database = os.getenv("NEO4J_DATABASE")
        
        # Validate required fields
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        if not neo4j_uri:
            raise ValueError(
                "NEO4J_URI environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        if not neo4j_username:
            raise ValueError(
                "NEO4J_USERNAME environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        if not neo4j_password:
            raise ValueError(
                "NEO4J_PASSWORD environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        if not neo4j_database:
            raise ValueError(
                "NEO4J_DATABASE environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        # Get optional parameters with defaults
        chunk_size = cls._get_int_env("CHUNK_SIZE", 1000)
        chunk_overlap = cls._get_int_env("CHUNK_OVERLAP", 200)
        top_k_results = cls._get_int_env("TOP_K_RESULTS", 5)
        rrf_constant = cls._get_int_env("RRF_CONSTANT", 60)
        entity_similarity_threshold = cls._get_float_env("ENTITY_SIMILARITY_THRESHOLD", 0.85)
        embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        answer_timeout = cls._get_int_env("ANSWER_TIMEOUT", 30)
        multi_hop_timeout = cls._get_int_env("MULTI_HOP_TIMEOUT", 45)
        max_pdf_size_mb = cls._get_int_env("MAX_PDF_SIZE_MB", 50)
        
        # Validate value ranges
        if chunk_size <= 0:
            logger.warning(
                f"Invalid CHUNK_SIZE ({chunk_size}). Must be positive. Using default: 1000"
            )
            chunk_size = 1000
        
        if chunk_overlap < 0:
            logger.warning(
                f"Invalid CHUNK_OVERLAP ({chunk_overlap}). Must be non-negative. Using default: 200"
            )
            chunk_overlap = 200
        
        if chunk_overlap >= chunk_size:
            logger.warning(
                f"CHUNK_OVERLAP ({chunk_overlap}) must be less than CHUNK_SIZE ({chunk_size}). "
                f"Using default overlap: 200"
            )
            chunk_overlap = 200
        
        if top_k_results <= 0:
            logger.warning(
                f"Invalid TOP_K_RESULTS ({top_k_results}). Must be positive. Using default: 5"
            )
            top_k_results = 5
        
        if entity_similarity_threshold < 0 or entity_similarity_threshold > 1:
            logger.warning(
                f"Invalid ENTITY_SIMILARITY_THRESHOLD ({entity_similarity_threshold}). "
                f"Must be between 0 and 1. Using default: 0.85"
            )
            entity_similarity_threshold = 0.85
        
        if answer_timeout <= 0:
            logger.warning(
                f"Invalid ANSWER_TIMEOUT ({answer_timeout}). Must be positive. Using default: 30"
            )
            answer_timeout = 30
        
        if multi_hop_timeout <= 0:
            logger.warning(
                f"Invalid MULTI_HOP_TIMEOUT ({multi_hop_timeout}). Must be positive. Using default: 45"
            )
            multi_hop_timeout = 45
        
        if max_pdf_size_mb <= 0:
            logger.warning(
                f"Invalid MAX_PDF_SIZE_MB ({max_pdf_size_mb}). Must be positive. Using default: 50"
            )
            max_pdf_size_mb = 50
        
        # Create and return config object
        return cls(
            openai_api_key=openai_api_key,
            neo4j_uri=neo4j_uri,
            neo4j_username=neo4j_username,
            neo4j_password=neo4j_password,
            neo4j_database=neo4j_database,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            top_k_results=top_k_results,
            rrf_constant=rrf_constant,
            entity_similarity_threshold=entity_similarity_threshold,
            embedding_model=embedding_model,
            answer_timeout=answer_timeout,
            multi_hop_timeout=multi_hop_timeout,
            max_pdf_size_mb=max_pdf_size_mb,
        )
    
    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """
        Get integer value from environment variable with default.
        
        Args:
            key: Environment variable name
            default: Default value if not set or invalid
            
        Returns:
            int: Integer value from environment or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        
        try:
            return int(value)
        except ValueError:
            logger.warning(
                f"Invalid value for {key}: '{value}'. Must be an integer. Using default: {default}"
            )
            return default
    
    @staticmethod
    def _get_float_env(key: str, default: float) -> float:
        """
        Get float value from environment variable with default.
        
        Args:
            key: Environment variable name
            default: Default value if not set or invalid
            
        Returns:
            float: Float value from environment or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        
        try:
            return float(value)
        except ValueError:
            logger.warning(
                f"Invalid value for {key}: '{value}'. Must be a number. Using default: {default}"
            )
            return default
