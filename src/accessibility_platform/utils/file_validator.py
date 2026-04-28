"""File validation and routing module.

This module provides secure file type detection and routing functionality.
It validates files based on both extension and MIME type to prevent security issues.
"""

import mimetypes
import os
from pathlib import Path

from ..config import Config


# ============================================================================
# Custom Exceptions
# ============================================================================

class UnsupportedFileTypeError(Exception):
    """Raised when a file type is not supported by the platform."""
    pass


class SecurityError(Exception):
    """Raised when a security validation fails (e.g., MIME type mismatch)."""
    pass


class FileSizeError(Exception):
    """Raised when a file exceeds the maximum allowed size."""
    pass


# ============================================================================
# File Validation Functions
# ============================================================================

def validate_file_type(file_path: str) -> str:
    """Validate file type using both extension and MIME type checking.
    
    This function performs security validation to ensure:
    1. The file extension is supported
    2. The MIME type matches the expected type for that extension
    3. The file size is within limits
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        The file extension (e.g., '.pdf', '.jpg')
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        UnsupportedFileTypeError: If the file extension is not supported
        SecurityError: If MIME type doesn't match the extension
        FileSizeError: If file exceeds maximum size limit
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file extension (lowercase for case-insensitive comparison)
    file_extension = Path(file_path).suffix.lower()
    
    # Check if extension is supported
    if file_extension not in Config.VALID_FILE_TYPES:
        supported = ", ".join(Config.get_supported_extensions())
        raise UnsupportedFileTypeError(
            f"Unsupported file type: {file_extension}. "
            f"Supported types: {supported}"
        )
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size > Config.MAX_FILE_SIZE_BYTES:
        max_size_mb = Config.MAX_FILE_SIZE_MB
        actual_size_mb = file_size / (1024 * 1024)
        raise FileSizeError(
            f"File size ({actual_size_mb:.2f} MB) exceeds maximum "
            f"allowed size ({max_size_mb} MB)"
        )
    
    # Validate MIME type matches extension (security check)
    # This prevents attacks where someone renames a malicious file
    # Example: malware.exe renamed to document.pdf
    detected_mime_type = _detect_mime_type(file_path)
    expected_mime_type = Config.get_mime_type(file_extension)
    
    if detected_mime_type != expected_mime_type:
        raise SecurityError(
            f"MIME type mismatch for {file_extension} file. "
            f"Expected: {expected_mime_type}, "
            f"Detected: {detected_mime_type}. "
            f"This may indicate a security issue."
        )
    
    return file_extension


def route_file(file_path: str) -> str:
    """Determine the file type category for routing to appropriate processor.
    
    This function validates the file and returns its category, which is used
    to route the file to the correct processor (PDF, image, or audio).
    
    Args:
        file_path: Path to the file to route
        
    Returns:
        File type category: "pdf", "image", or "audio"
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        UnsupportedFileTypeError: If the file extension is not supported
        SecurityError: If MIME type doesn't match the extension
        FileSizeError: If file exceeds maximum size limit
    """
    # Validate the file first (this will raise exceptions if invalid)
    file_extension = validate_file_type(file_path)
    
    # Route based on extension
    if file_extension == ".pdf":
        return "pdf"
    elif file_extension in [".jpg", ".jpeg", ".png"]:
        return "image"
    elif file_extension in [".mp3", ".wav"]:
        return "audio"
    else:
        # This should never happen if Config.VALID_FILE_TYPES is correct
        raise UnsupportedFileTypeError(f"Unknown file type: {file_extension}")


# ============================================================================
# Helper Functions
# ============================================================================

def _detect_mime_type(file_path: str) -> str:
    """Detect the MIME type of a file.
    
    This uses Python's mimetypes module to guess the MIME type based on
    the file extension. For more robust detection, you could use libraries
    like python-magic that read file headers, but mimetypes is sufficient
    for our use case and doesn't require additional dependencies.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Detected MIME type (e.g., "application/pdf")
    """
    # Initialize mimetypes if not already done
    if not mimetypes.inited:
        mimetypes.init()
    
    # Guess MIME type from file extension
    mime_type, _ = mimetypes.guess_type(file_path)
    
    # If mimetypes can't determine it, return a generic type
    if mime_type is None:
        return "application/octet-stream"
    
    return mime_type


def get_file_info(file_path: str) -> dict:
    """Get detailed information about a file.
    
    This is a utility function that returns various file metadata.
    Useful for debugging and logging.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information:
        - name: File name
        - extension: File extension
        - size_bytes: File size in bytes
        - size_mb: File size in megabytes
        - mime_type: Detected MIME type
        - category: File category (pdf/image/audio)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = os.path.getsize(file_path)
    file_extension = Path(file_path).suffix.lower()
    
    try:
        category = route_file(file_path)
    except Exception:
        category = "unknown"
    
    return {
        "name": Path(file_path).name,
        "extension": file_extension,
        "size_bytes": file_size,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "mime_type": _detect_mime_type(file_path),
        "category": category,
    }
