"""
Logging utility for the Hybrid GraphRAG Chatbot.

This module provides logging functionality with credential masking
and configurable log levels.
"""

import logging
import os
import re
from typing import Optional


# Patterns for sensitive information that should be masked
SENSITIVE_PATTERNS = [
    r'password["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',  # password=xxx or password: xxx
    r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',  # api_key=xxx or apiKey: xxx
    r'token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',  # token=xxx
    r'secret["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',  # secret=xxx
    r'bearer\s+([^\s]+)',  # Bearer xxx
]


def mask_sensitive_info(message: str) -> str:
    """
    Mask sensitive information in log messages.
    
    This function replaces sensitive values (passwords, API keys, tokens)
    with asterisks to prevent credential leakage in logs.
    
    Args:
        message: Log message that may contain sensitive information
        
    Returns:
        str: Message with sensitive information masked
        
    Example:
        >>> mask_sensitive_info("password=secret123")
        'password=***'
        >>> mask_sensitive_info("api_key=sk-1234567890")
        'api_key=***'
    """
    masked_message = message
    
    for pattern in SENSITIVE_PATTERNS:
        # Replace the captured group (the sensitive value) with ***
        masked_message = re.sub(
            pattern,
            lambda m: m.group(0).replace(m.group(1), "***"),
            masked_message,
            flags=re.IGNORECASE
        )
    
    return masked_message


class SensitiveInfoFilter(logging.Filter):
    """
    Logging filter that masks sensitive information in log records.
    
    This filter is applied to all log handlers to ensure that
    sensitive information is never written to log files or console.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record by masking sensitive information.
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: Always True (we don't filter out records, just modify them)
        """
        # Mask sensitive info in the message
        record.msg = mask_sensitive_info(str(record.msg))
        
        # Mask sensitive info in arguments if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: mask_sensitive_info(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    mask_sensitive_info(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        
        return True


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with the specified configuration.
    
    This function creates a logger with:
    - Timestamp in log messages
    - Component name (logger name)
    - Log level
    - Sensitive information masking
    
    Args:
        name: Name of the logger (usually __name__ of the module)
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to INFO.
        log_file: Optional path to log file. If None, logs only to console.
        
    Returns:
        logging.Logger: Configured logger instance
        
    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Processing document")
        2024-01-15 10:30:45 - my_module - INFO - Processing document
    """
    # Get log level from parameter or environment variable
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level not in valid_levels:
        level = "INFO"
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter with timestamp, component name, and level
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level))
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveInfoFilter())
    logger.addHandler(console_handler)
    
    # Create file handler if log_file is specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveInfoFilter())
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def log_llm_call(
    logger: logging.Logger,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: int
) -> None:
    """
    Log LLM API call with metrics.
    
    This function logs LLM API calls with token usage and latency
    for monitoring and debugging purposes.
    
    Args:
        logger: Logger instance to use
        model: Name of the LLM model used
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total number of tokens used
        latency_ms: Time taken for the API call in milliseconds
        
    Example:
        >>> log_llm_call(logger, "gpt-4o-mini", 100, 50, 150, 1200)
        2024-01-15 10:30:45 - my_module - INFO - LLM call: model=gpt-4o-mini, 
        prompt_tokens=100, completion_tokens=50, total_tokens=150, latency_ms=1200
    """
    logger.info(
        f"LLM call: model={model}, prompt_tokens={prompt_tokens}, "
        f"completion_tokens={completion_tokens}, total_tokens={total_tokens}, "
        f"latency_ms={latency_ms}"
    )


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    component: str,
    operation: str,
    **context
) -> None:
    """
    Log error with contextual information.
    
    This function logs errors with the component name, operation being performed,
    and additional context to help with debugging.
    
    Args:
        logger: Logger instance to use
        error: Exception that occurred
        component: Name of the component where error occurred
        operation: Operation being performed when error occurred
        **context: Additional context as keyword arguments
        
    Example:
        >>> log_error_with_context(
        ...     logger, 
        ...     ValueError("Invalid input"), 
        ...     "PDFLoader", 
        ...     "load_pdf",
        ...     file_path="/path/to/file.pdf"
        ... )
        2024-01-15 10:30:45 - my_module - ERROR - Error in PDFLoader during load_pdf: 
        Invalid input. Context: file_path=/path/to/file.pdf
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    logger.error(
        f"Error in {component} during {operation}: {str(error)}. "
        f"Context: {context_str}"
    )


def create_user_friendly_error(error: Exception, operation: str) -> str:
    """
    Create a user-friendly error message from an exception.
    
    This function converts technical error messages into user-friendly
    messages that don't expose internal implementation details.
    
    Args:
        error: Exception that occurred
        operation: Operation that failed
        
    Returns:
        str: User-friendly error message
        
    Example:
        >>> create_user_friendly_error(
        ...     ConnectionError("Connection refused"), 
        ...     "connecting to Neo4j"
        ... )
        'Failed to connect to Neo4j. Please check your connection settings and try again.'
    """
    error_type = type(error).__name__
    
    # Map technical errors to user-friendly messages
    if "Connection" in error_type or "connection" in str(error).lower():
        return (
            f"Failed to connect while {operation}. "
            "Please check your connection settings and try again."
        )
    elif "Authentication" in error_type or "auth" in str(error).lower():
        return (
            f"Authentication failed while {operation}. "
            "Please check your credentials and try again."
        )
    elif "Timeout" in error_type or "timeout" in str(error).lower():
        return (
            f"Operation timed out while {operation}. "
            "Please try again or check your network connection."
        )
    elif "FileNotFound" in error_type:
        return (
            f"File not found while {operation}. "
            "Please check the file path and try again."
        )
    elif "Permission" in error_type or "permission" in str(error).lower():
        return (
            f"Permission denied while {operation}. "
            "Please check file permissions and try again."
        )
    else:
        return (
            f"An error occurred while {operation}. "
            "Please check your input and try again."
        )
