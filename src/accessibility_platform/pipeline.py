"""Processing pipeline orchestration."""

import time

from openai import OpenAI

from .config import Config
from .cost_tracker import CostTracker
from .models import AccessibilityResult, ProcessingState
from .processors.audio_processor import process_audio
from .processors.embedder import embed_chunks
from .processors.image_processor import process_image
from .processors.normalizer import normalize_text
from .processors.pdf_processor import process_pdf
from .processors.summarizer import summarize
from .utils.file_validator import route_file
from .vector_db.chroma_client import VectorDBClient


class ProcessingPipeline:
    """Orchestrates the entire file processing workflow."""
    
    def __init__(self):
        """Initialize pipeline components."""
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.vector_db = VectorDBClient()
    
    def process_file(self, file_path: str, file_id: str) -> AccessibilityResult:
        """Process a file end-to-end.
        
        Args:
            file_path: Path to the file
            file_id: Unique file identifier
            
        Returns:
            AccessibilityResult with all processed data
        """
        start_time = time.time()
        cost_tracker = CostTracker()
        
        try:
            # Route to appropriate processor
            file_type = route_file(file_path)
            
            # Create processing state
            state = ProcessingState(
                file_path=file_path,
                file_id=file_id,
                file_type=file_type
            )
            
            # Step 1: Extract content
            if file_type == "pdf":
                state = process_pdf(state, self.openai_client, cost_tracker)
            elif file_type == "image":
                state = process_image(state, self.openai_client, cost_tracker)
            elif file_type == "audio":
                state = process_audio(state)
            
            if state.error:
                raise Exception(state.error)
            
            # Step 2: Normalize and chunk
            state = normalize_text(state)
            if state.error:
                raise Exception(state.error)
            
            # Step 3: Summarize
            state = summarize(state, self.openai_client, cost_tracker)
            if state.error:
                raise Exception(state.error)
            
            # Step 4: Embed and store
            state = embed_chunks(state, self.openai_client, self.vector_db, cost_tracker)
            if state.error:
                raise Exception(state.error)
            
            # Build result
            processing_time = time.time() - start_time
            cost_summary = cost_tracker.get_cost_summary(file_id=file_id)
            
            return AccessibilityResult(
                file_id=file_id,
                file_name=file_path.split("/")[-1],
                transcript=state.raw_text,
                summary=state.summary,
                key_points=state.key_points,
                tags=state.tags,
                cost_summary=cost_summary,
                processing_time_seconds=round(processing_time, 2)
            )
            
        except Exception as e:
            # Return error result
            processing_time = time.time() - start_time
            cost_summary = cost_tracker.get_cost_summary(file_id=file_id)
            
            return AccessibilityResult(
                file_id=file_id,
                file_name=file_path.split("/")[-1],
                transcript=f"Error: {str(e)}",
                summary="",
                key_points=[],
                tags=[],
                cost_summary=cost_summary,
                processing_time_seconds=round(processing_time, 2)
            )
