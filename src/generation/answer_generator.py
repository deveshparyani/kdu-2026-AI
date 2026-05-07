"""
Answer generation module using LLM with retrieved context.

This module generates final answers by combining retrieved context
with LLM reasoning.
"""

from typing import List, Tuple, Dict, Any
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.utils.logger import setup_logger, log_error_with_context, log_llm_call
import time

logger = setup_logger(__name__)


class AnswerGenerator:
    """
    Generates answers using LLM with retrieved context.
    
    This class:
    - Formats retrieved context for LLM
    - Generates answers with source references
    - Enforces timeouts
    - Logs LLM calls with metrics
    
    Attributes:
        llm: ChatOpenAI instance for answer generation
        timeout: Maximum response time in seconds
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-nano",
        timeout: int = 30
    ):
        """
        Initialize with LLM and timeout.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model name (default: "gpt-4o-mini")
            timeout: Maximum response time in seconds (default: 30)
        """
        logger.info(f"Initializing AnswerGenerator with model='{model}', timeout={timeout}s")
        
        self.timeout = timeout
        
        try:
            self.llm = ChatOpenAI(
                api_key=api_key,
                model=model,
                temperature=0.7,  # Slightly creative for natural answers
                request_timeout=timeout
            )
            
            logger.info("AnswerGenerator initialized successfully")
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="AnswerGenerator",
                operation="initialization",
                model=model
            )
            raise
    
    def generate_answer(
        self,
        query: str,
        context: List[Tuple[Document, float]]
    ) -> Dict[str, Any]:
        """
        Generate answer with source references.
        
        This method:
        1. Formats context documents for LLM
        2. Creates prompt with query and context
        3. Generates answer using LLM
        4. Extracts source references
        5. Returns answer with sources and metadata
        
        Args:
            query: User query
            context: List of (Document, score) tuples from reranker
            
        Returns:
            Dict[str, Any]: Dictionary with:
                - answer: Generated answer text
                - sources: List of source documents used
                - num_sources: Number of sources used
                - latency_ms: Time taken to generate answer
            
        Raises:
            TimeoutError: If generation exceeds timeout
            
        Example:
            >>> generator = AnswerGenerator(api_key="sk-...")
            >>> context = [(doc1, 0.9), (doc2, 0.8)]
            >>> result = generator.generate_answer("What is ML?", context)
            >>> print(result['answer'])
            >>> print(f"Used {result['num_sources']} sources")
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to generate_answer")
            return {
                "answer": "I cannot answer an empty question.",
                "sources": [],
                "num_sources": 0,
                "latency_ms": 0
            }
        
        if not context:
            logger.warning("No context provided to generate_answer")
            return {
                "answer": "I don't have enough information to answer this question.",
                "sources": [],
                "num_sources": 0,
                "latency_ms": 0
            }
        
        logger.info(f"Generating answer for query: '{query[:100]}...' with {len(context)} context documents")
        
        try:
            # Format context for LLM
            formatted_context = self._format_context(context)
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful AI assistant that answers questions based on the provided context.

Instructions:
1. Answer the question using ONLY the information from the context
2. If the context doesn't contain enough information, say so
3. Be concise but complete in your answer
4. Reference specific sources when making claims
5. If multiple sources provide different information, mention both perspectives

Format your answer naturally, as if explaining to a colleague."""),
                ("human", """Context:
{context}

Question: {query}

Please provide a clear and accurate answer based on the context above.""")
            ])
            
            # Track time
            start_time = time.time()
            
            # Generate answer
            chain = prompt | self.llm
            response = chain.invoke({
                "query": query,
                "context": formatted_context
            })
            
            answer = response.content.strip()
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log LLM call
            log_llm_call(
                logger,
                model=self.llm.model_name,
                prompt_tokens=len(formatted_context) // 4 + len(query) // 4,  # Rough estimate
                completion_tokens=len(answer) // 4,  # Rough estimate
                total_tokens=(len(formatted_context) + len(query) + len(answer)) // 4,
                latency_ms=latency_ms
            )
            
            # Extract sources
            sources = [doc for doc, score in context]
            
            logger.info(f"Answer generated successfully in {latency_ms}ms")
            
            return {
                "answer": answer,
                "sources": sources,
                "num_sources": len(sources),
                "latency_ms": latency_ms
            }
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="AnswerGenerator",
                operation="generate_answer",
                query=query[:100],
                num_context_docs=len(context)
            )
            
            # Return error message
            return {
                "answer": "I encountered an error while generating the answer. Please try again.",
                "sources": [],
                "num_sources": 0,
                "latency_ms": 0
            }
    
    def _format_context(self, context: List[Tuple[Document, float]]) -> str:
        """
        Format context documents for LLM prompt.
        
        This method creates a readable format with:
        - Document number
        - Content
        - Source information
        - Relevance score
        
        Args:
            context: List of (Document, score) tuples
            
        Returns:
            str: Formatted context string
        """
        formatted_parts = []
        
        for i, (doc, score) in enumerate(context, 1):
            # Get source information
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "N/A")
            
            # Format document
            doc_text = f"""Document {i} (Relevance: {score:.3f}):
Source: {source}, Page: {page}
Content: {doc.page_content}
"""
            formatted_parts.append(doc_text)
        
        return "\n---\n".join(formatted_parts)
