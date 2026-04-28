"""Cost tracking module for API calls.

This module tracks all API calls (vision, embeddings, summarization) and calculates
costs based on token usage and pricing information from the config.
"""

from typing import Dict, List, Optional

from .config import Config
from .models import CostEntry, CostSummary


class CostTracker:
    """Tracks API costs across all operations.
    
    This class maintains a list of all API calls made during processing
    and provides methods to calculate cost summaries by file, operation, or model.
    
    Example usage:
        tracker = CostTracker()
        
        # Log an API call
        tracker.log_api_call(
            model="gpt-4o-mini",
            operation="summarization",
            prompt_tokens=1000,
            completion_tokens=200,
            file_id="file-123"
        )
        
        # Get cost summary
        summary = tracker.get_cost_summary(file_id="file-123")
        print(f"Total cost: ${summary['total_cost_usd']}")
    """
    
    def __init__(self):
        """Initialize the cost tracker with an empty list of entries."""
        self._entries: List[CostEntry] = []
    
    def log_api_call(
        self,
        model: str,
        operation: str,
        prompt_tokens: int,
        completion_tokens: int,
        file_id: str
    ) -> CostEntry:
        """Log an API call and calculate its cost.
        
        This method calculates the cost based on the pricing table in Config
        and stores the entry for later aggregation.
        
        Args:
            model: Name of the AI model (e.g., "gpt-4o-mini")
            operation: Type of operation (e.g., "vision", "embedding", "summarization")
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            file_id: ID of the file being processed
            
        Returns:
            The created CostEntry object
            
        Raises:
            ValueError: If model is not in pricing table or tokens are negative
        """
        # Validate inputs
        if prompt_tokens < 0 or completion_tokens < 0:
            raise ValueError("Token counts cannot be negative")
        
        # Check if model exists in pricing table
        if model not in Config.PRICING:
            raise ValueError(
                f"Model '{model}' not found in pricing table. "
                f"Available models: {list(Config.PRICING.keys())}"
            )
        
        # Calculate cost
        cost_usd = self._calculate_cost(model, prompt_tokens, completion_tokens)
        
        # Create cost entry
        entry = CostEntry(
            model=model,
            operation=operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            file_id=file_id
        )
        
        # Store entry
        self._entries.append(entry)
        
        return entry
    
    def get_cost_summary(self, file_id: Optional[str] = None) -> CostSummary:
        """Get a cost summary for one or all files.
        
        This aggregates all cost entries and provides breakdowns by operation
        and model type.
        
        Args:
            file_id: ID of specific file (None = all files)
            
        Returns:
            CostSummary with aggregated cost information
        """
        # Filter entries by file_id if specified
        if file_id is not None:
            entries = [e for e in self._entries if e.file_id == file_id]
        else:
            entries = self._entries
        
        # If no entries, return zero summary
        if not entries:
            return CostSummary(
                file_id=file_id,
                total_cost_usd=0.0,
                by_operation={},
                by_model={},
                total_tokens=0
            )
        
        # Calculate total cost
        total_cost = sum(e.cost_usd for e in entries)
        
        # Calculate total tokens
        total_tokens = sum(e.prompt_tokens + e.completion_tokens for e in entries)
        
        # Aggregate by operation
        by_operation: Dict[str, float] = {}
        for entry in entries:
            if entry.operation not in by_operation:
                by_operation[entry.operation] = 0.0
            by_operation[entry.operation] += entry.cost_usd
        
        # Aggregate by model
        by_model: Dict[str, float] = {}
        for entry in entries:
            if entry.model not in by_model:
                by_model[entry.model] = 0.0
            by_model[entry.model] += entry.cost_usd
        
        return CostSummary(
            file_id=file_id,
            total_cost_usd=round(total_cost, 6),  # Round to 6 decimal places
            by_operation=by_operation,
            by_model=by_model,
            total_tokens=total_tokens
        )
    
    def get_all_entries(self, file_id: Optional[str] = None) -> List[CostEntry]:
        """Get all cost entries, optionally filtered by file_id.
        
        Args:
            file_id: ID of specific file (None = all files)
            
        Returns:
            List of CostEntry objects
        """
        if file_id is not None:
            return [e for e in self._entries if e.file_id == file_id]
        return self._entries.copy()
    
    def clear(self, file_id: Optional[str] = None) -> None:
        """Clear cost entries.
        
        Args:
            file_id: ID of specific file to clear (None = clear all)
        """
        if file_id is not None:
            self._entries = [e for e in self._entries if e.file_id != file_id]
        else:
            self._entries.clear()
    
    def get_total_cost(self, file_id: Optional[str] = None) -> float:
        """Get total cost across all entries.
        
        Args:
            file_id: ID of specific file (None = all files)
            
        Returns:
            Total cost in USD
        """
        summary = self.get_cost_summary(file_id)
        return summary["total_cost_usd"]
    
    def _calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate cost for an API call.
        
        Uses the pricing table from Config to calculate cost based on token usage.
        
        Args:
            model: Name of the AI model
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        pricing = Config.PRICING[model]
        
        # Calculate input cost (per 1,000 tokens)
        input_cost = (prompt_tokens / 1000) * pricing["input_per_1k"]
        
        # Calculate output cost (per 1,000 tokens)
        output_cost = (completion_tokens / 1000) * pricing["output_per_1k"]
        
        # Total cost
        total_cost = input_cost + output_cost
        
        return total_cost
    
    def __len__(self) -> int:
        """Return the number of cost entries."""
        return len(self._entries)
    
    def __repr__(self) -> str:
        """Return string representation of the cost tracker."""
        total_cost = self.get_total_cost()
        return f"CostTracker(entries={len(self._entries)}, total_cost=${total_cost:.6f})"
