"""Retrieval-Augmented Generation chat service."""

from openai import OpenAI

from ..config import Config
from ..database.chat_db import ChatDatabase
from ..search.hybrid_search import HybridSearchService


class RAGChatService:
    """Chat service with RAG capabilities."""
    
    def __init__(
        self,
        chat_db: ChatDatabase,
        search_service: HybridSearchService,
        openai_client: OpenAI
    ):
        """Initialize RAG chat service."""
        self.chat_db = chat_db
        self.search_service = search_service
        self.openai_client = openai_client
    
    def answer_question(
        self,
        conversation_id: str,
        query: str
    ) -> str:
        """Answer a question using RAG.
        
        Args:
            conversation_id: Conversation ID
            query: User question
            
        Returns:
            AI-generated answer
        """
        # Get current file context
        current_file = self.chat_db.get_current_file(conversation_id)
        
        # Retrieve relevant chunks
        if current_file:
            search_results = self.search_service.search(
                query=query,
                top_k=3,
                file_filter=current_file
            )
            context = "\n\n".join([r["text"] for r in search_results])
        else:
            context = "No file uploaded yet."
        
        # Get conversation history
        history = self.chat_db.get_conversation_history(conversation_id, limit=10)
        
        # Build messages
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that answers questions about uploaded documents. Use the provided context to answer accurately."
            }
        ]
        
        # Add history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current query with context
        user_message = f"Context:\n{context}\n\nQuestion: {query}"
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Call OpenAI
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        answer = response.choices[0].message.content
        
        # Store in database
        self.chat_db.add_message(conversation_id, "user", query)
        self.chat_db.add_message(conversation_id, "assistant", answer)
        
        return answer
