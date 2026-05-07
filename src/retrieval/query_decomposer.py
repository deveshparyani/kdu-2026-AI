"""
Query decomposition module for breaking complex queries into simpler sub-queries.

This module uses LLM to analyze query complexity and decompose multi-hop
queries into simpler sub-queries for better retrieval.
"""

from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.utils.logger import setup_logger, log_error_with_context

logger = setup_logger(__name__)


class QueryDecomposer:
    """
    Decomposes complex queries into simpler sub-queries.
    
    This class uses an LLM to:
    - Analyze if a query is complex and needs decomposition
    - Break complex queries into simpler sub-queries
    - Preserve query intent and relationships
    - Fall back to original query if decomposition fails
    
    Attributes:
        llm: ChatOpenAI instance for query analysis
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4.1-nano"):
        """
        Initialize with LLM for query analysis.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model name (default: "gpt-4o-mini")
        """
        logger.info(f"Initializing QueryDecomposer with model='{model}'")
        
        try:
            self.llm = ChatOpenAI(
                api_key=api_key,
                model=model,
                temperature=0  # Use deterministic output
            )
            
            logger.info("QueryDecomposer initialized successfully")
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="QueryDecomposer",
                operation="initialization",
                model=model
            )
            raise
    
    def decompose(self, query: str) -> List[str]:
        """
        Decompose query if complex, otherwise return original.
        
        This method:
        1. Analyzes if the query is complex (multi-hop)
        2. If complex, breaks it into simpler sub-queries
        3. If simple or decomposition fails, returns original query
        
        Args:
            query: User query to analyze
            
        Returns:
            List[str]: List of sub-queries (or single original query if not complex)
            
        Example:
            >>> decomposer = QueryDecomposer(api_key="sk-...")
            >>> query = "Who is the CEO of the company that John Smith works for?"
            >>> sub_queries = decomposer.decompose(query)
            >>> print(sub_queries)
            ['What company does John Smith work for?', 'Who is the CEO of that company?']
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to decompose")
            return [query]
        
        logger.info(f"Analyzing query for decomposition: '{query}'")
        
        try:
            # Create prompt for query decomposition
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a query decomposition expert. Your task is to analyze if a query is complex and needs to be broken down into simpler sub-queries.

A complex query typically:
- Requires multiple hops through relationships (e.g., "Who is X's boss's boss?")
- Asks about indirect connections (e.g., "What company does John's colleague work for?")
- Requires combining information from multiple sources

If the query is complex, break it down into 2-4 simpler sub-queries that can be answered sequentially.
If the query is simple (can be answered directly), respond with "SIMPLE".

Format your response as:
- If simple: Just write "SIMPLE"
- If complex: Write each sub-query on a new line, numbered like:
1. First sub-query
2. Second sub-query
3. Third sub-query

Examples:

Query: "What is machine learning?"
Response: SIMPLE

Query: "Who is the CEO of the company that John Smith works for?"
Response:
1. What company does John Smith work for?
2. Who is the CEO of that company?

Query: "What locations are connected to Entity X through Entity Y?"
Response:
1. What is the relationship between Entity X and Entity Y?
2. What locations are connected to Entity Y?
"""),
                ("human", "{query}")
            ])
            
            # Get LLM response
            chain = prompt | self.llm
            response = chain.invoke({"query": query})
            response_text = response.content.strip()
            
            logger.debug(f"LLM response: {response_text}")
            
            # Parse response
            if response_text == "SIMPLE":
                logger.info("Query is simple, no decomposition needed")
                return [query]
            
            # Extract sub-queries
            sub_queries = []
            for line in response_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Remove numbering (e.g., "1. " or "1) ")
                if line[0].isdigit():
                    # Find the first space or period after the number
                    for i, char in enumerate(line):
                        if char in ['.', ')', ' '] and i > 0:
                            line = line[i+1:].strip()
                            break
                
                if line:
                    sub_queries.append(line)
            
            if sub_queries:
                logger.info(f"Decomposed query into {len(sub_queries)} sub-queries")
                for i, sq in enumerate(sub_queries, 1):
                    logger.debug(f"  Sub-query {i}: {sq}")
                return sub_queries
            else:
                logger.warning("Failed to extract sub-queries, using original query")
                return [query]
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="QueryDecomposer",
                operation="decompose",
                query=query
            )
            # Fall back to original query on error
            logger.info("Falling back to original query due to error")
            return [query]
    
    def is_complex_query(self, query: str) -> bool:
        """
        Check if a query is complex without decomposing it.
        
        Args:
            query: Query to analyze
            
        Returns:
            bool: True if query is complex, False otherwise
        """
        sub_queries = self.decompose(query)
        return len(sub_queries) > 1
