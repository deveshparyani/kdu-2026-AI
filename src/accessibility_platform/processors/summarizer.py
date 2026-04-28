"""Text summarization with hallucination prevention."""

import json

import tiktoken
from openai import OpenAI

from ..config import Config
from ..cost_tracker import CostTracker
from ..models import ProcessingState


def summarize(
    state: ProcessingState,
    openai_client: OpenAI,
    cost_tracker: CostTracker
) -> ProcessingState:
    """Generate summary, key points, and tags.
    
    Args:
        state: ProcessingState with raw_text set
        openai_client: OpenAI client instance
        cost_tracker: CostTracker instance
        
    Returns:
        Updated ProcessingState with summary, key_points, tags
    """
    try:
        print(f"Summarizing text. Raw text length: {len(state.raw_text)}")
        
        # Check if raw_text is empty
        if not state.raw_text or len(state.raw_text.strip()) == 0:
            print("Warning: raw_text is empty, skipping summarization")
            state.summary = "No content to summarize"
            state.key_points = ["No content available"]
            state.tags = ["empty"]
            return state
        
        # Truncate text to max tokens
        truncated_text = _truncate_text(state.raw_text, Config.MAX_SUMMARY_INPUT_TOKENS)
        print(f"Truncated text length: {len(truncated_text)}")
        
        # Create prompt
        prompt = f"""Analyze the following text and provide:
1. A concise summary (150 words max)
2. 5-7 key points as bullet points
3. 3-5 topic tags

Text:
{truncated_text}

Respond in JSON format:
{{
  "summary": "...",
  "key_points": ["...", "..."],
  "tags": ["...", "..."]
}}"""
        
        print("Calling OpenAI API for summarization...")
        # Call OpenAI API with JSON mode
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes documents accurately. Only use information from the provided text."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # Low temperature for consistency
            max_tokens=500
        )
        
        print("OpenAI API response received")
        
        # Parse response
        result = json.loads(response.choices[0].message.content)
        print(f"Parsed result: {result.keys()}")
        
        state.summary = result.get("summary", "")
        state.key_points = result.get("key_points", [])
        state.tags = result.get("tags", [])
        
        print(f"Summary length: {len(state.summary)}")
        print(f"Key points count: {len(state.key_points)}")
        print(f"Tags count: {len(state.tags)}")
        
        # Log cost
        cost_tracker.log_api_call(
            model="gpt-4o-mini",
            operation="summarization",
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            file_id=state.file_id
        )
        
        return state
        
    except Exception as e:
        print(f"Summarization error: {str(e)}")
        import traceback
        traceback.print_exc()
        state.error = f"Summarization failed: {str(e)}"
        return state


def _truncate_text(text: str, max_tokens: int) -> str:
    """Truncate text to max tokens."""
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        return text
    
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)
