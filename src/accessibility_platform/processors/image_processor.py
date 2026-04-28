"""Image processing module."""

from openai import OpenAI

from ..config import Config
from ..cost_tracker import CostTracker
from ..models import ProcessingState
from ..utils.vision_api import call_vision_api


def process_image(
    state: ProcessingState,
    openai_client: OpenAI,
    cost_tracker: CostTracker
) -> ProcessingState:
    """Process standalone image file.
    
    Args:
        state: ProcessingState with file_path set
        openai_client: OpenAI client instance
        cost_tracker: CostTracker instance
        
    Returns:
        Updated ProcessingState with raw_text populated
    """
    try:
        # Read image file
        with open(state.file_path, 'rb') as f:
            image_bytes = f.read()
        
        # Create prompt for vision API
        prompt = (
            "Describe this image in detail. "
            "If there is any text in the image, extract it verbatim. "
            "Provide a comprehensive description that would help someone "
            "who cannot see the image understand its content."
        )
        
        # Call vision API with caching
        description = call_vision_api(
            image_bytes=image_bytes,
            prompt=prompt,
            file_id=state.file_id,
            cost_tracker=cost_tracker,
            openai_client=openai_client
        )
        
        # Store description as raw_text
        state.raw_text = description
        
        return state
        
    except Exception as e:
        state.error = f"Image processing failed: {str(e)}"
        return state


def process_image_bytes(
    image_bytes: bytes,
    file_id: str,
    openai_client: OpenAI,
    cost_tracker: CostTracker,
    custom_prompt: str = None
) -> str:
    """Process image from bytes (utility function).
    
    Args:
        image_bytes: Image data as bytes
        file_id: ID of the file being processed
        openai_client: OpenAI client instance
        cost_tracker: CostTracker instance
        custom_prompt: Optional custom prompt (uses default if None)
        
    Returns:
        Description text from vision API
    """
    if custom_prompt is None:
        custom_prompt = (
            "Describe this image in detail. "
            "If there is any text in the image, extract it verbatim."
        )
    
    return call_vision_api(
        image_bytes=image_bytes,
        prompt=custom_prompt,
        file_id=file_id,
        cost_tracker=cost_tracker,
        openai_client=openai_client
    )
