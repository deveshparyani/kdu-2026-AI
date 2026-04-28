"""Audio processing using local Whisper model."""

import whisper

from ..models import ProcessingState


def process_audio(state: ProcessingState) -> ProcessingState:
    """Process audio file using local Whisper model.
    
    Args:
        state: ProcessingState with file_path set
        
    Returns:
        Updated ProcessingState with raw_text populated
    """
    try:
        print(f"Loading Whisper model...")
        # Load Whisper model (base model for balance of speed/accuracy)
        model = whisper.load_model("base")
        
        print(f"Transcribing audio file: {state.file_path}")
        # Transcribe audio
        result = model.transcribe(state.file_path)
        
        print(f"Transcription complete. Result keys: {result.keys()}")
        
        # Extract transcript
        transcript = result["text"]
        print(f"Transcript length: {len(transcript)}")
        
        # Format with timestamps if available
        if "segments" in result and result["segments"]:
            formatted_text = []
            for segment in result["segments"]:
                start_time = _format_timestamp(segment["start"])
                text = segment["text"].strip()
                formatted_text.append(f"[{start_time}] {text}")
            
            state.raw_text = "\n".join(formatted_text)
        else:
            state.raw_text = transcript
        
        print(f"Final raw_text length: {len(state.raw_text)}")
        return state
        
    except Exception as e:
        print(f"Audio processing error: {str(e)}")
        import traceback
        traceback.print_exc()
        state.error = f"Audio processing failed: {str(e)}"
        return state


def _format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS timestamp."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"
