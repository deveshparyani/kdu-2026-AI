"""
Cypher query generation module for converting natural language to Cypher.

This module uses LLM to generate Cypher queries from natural language
for querying the Neo4j knowledge graph.
"""

from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.storage.graph_store import GraphStore
from src.utils.logger import setup_logger, log_error_with_context

logger = setup_logger(__name__)


class CypherGenerator:
    """
    Generates Cypher queries from natural language.
    
    This class uses an LLM to:
    - Convert natural language questions to Cypher queries
    - Use graph schema as context for accurate generation
    - Handle generation failures gracefully
    
    Attributes:
        llm: ChatOpenAI instance for Cypher generation
        graph_store: GraphStore instance for schema access
    """
    
    def __init__(
        self,
        api_key: str,
        graph_store: GraphStore,
        model: str = "gpt-4.1-nano"
    ):
        """
        Initialize with LLM and graph store for schema access.
        
        Args:
            api_key: OpenAI API key
            graph_store: GraphStore instance for schema retrieval
            model: OpenAI model name (default: "gpt-4o-mini")
        """
        logger.info(f"Initializing CypherGenerator with model='{model}'")
        
        self.graph_store = graph_store
        
        try:
            self.llm = ChatOpenAI(
                api_key=api_key,
                model=model,
                temperature=0  # Use deterministic output for query generation
            )
            
            logger.info("CypherGenerator initialized successfully")
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="CypherGenerator",
                operation="initialization",
                model=model
            )
            raise
    
    def generate_cypher(self, query: str) -> Optional[str]:
        """
        Generate Cypher query from natural language.
        
        This method:
        1. Gets the graph schema from Neo4j
        2. Uses LLM to convert natural language to Cypher
        3. Returns the generated Cypher query
        4. Returns None if generation fails
        
        Args:
            query: Natural language query
            
        Returns:
            Optional[str]: Cypher query string or None if generation fails
            
        Example:
            >>> generator = CypherGenerator(api_key="sk-...", graph_store=graph_store)
            >>> cypher = generator.generate_cypher("Who works for OpenAI?")
            >>> print(cypher)
            MATCH (p:Person)-[:WORKS_FOR]->(o:Organization {name: 'OpenAI'})
            RETURN p.name
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to generate_cypher")
            return None
        
        logger.info(f"Generating Cypher for query: '{query}'")
        
        try:
            # Get graph schema
            schema = self.graph_store.get_schema()
            
            # Create prompt for Cypher generation
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a Cypher query expert. Your task is to convert natural language questions into Cypher queries for Neo4j.

Use the following graph schema:
{schema}

Rules for generating Cypher:
1. Use MATCH clauses to find patterns
2. Use WHERE clauses for filtering
3. Use RETURN to specify what to return
4. Use relationship patterns like (a)-[:REL_TYPE]->(b)
5. Use properties like {{name: 'value'}} for exact matches
6. Use CONTAINS for partial string matches
7. For multi-hop queries, chain multiple relationship patterns
8. Always return relevant information (names, properties, paths)
9. Limit results to 10 unless specified otherwise

Examples:

Question: "Who works for OpenAI?"
Cypher: MATCH (p:Person)-[:WORKS_FOR]->(o:Organization {{name: 'OpenAI'}}) RETURN p.name LIMIT 10

Question: "What organizations are located in San Francisco?"
Cypher: MATCH (o:Organization)-[:LOCATED_IN]->(l:Location {{name: 'San Francisco'}}) RETURN o.name LIMIT 10

Question: "Who is connected to John Smith?"
Cypher: MATCH (p:Person {{name: 'John Smith'}})-[r]-(connected) RETURN connected.name, type(r) LIMIT 10

Question: "What is the relationship between Entity A and Entity B?"
Cypher: MATCH path = (a)-[*1..3]-(b) WHERE a.name = 'Entity A' AND b.name = 'Entity B' RETURN path LIMIT 10

Now generate a Cypher query for the following question. Return ONLY the Cypher query, no explanations.
"""),
                ("human", "{query}")
            ])
            
            # Generate Cypher
            chain = prompt | self.llm
            response = chain.invoke({"query": query, "schema": schema})
            cypher_query = response.content.strip()
            
            # Remove markdown code blocks if present
            if cypher_query.startswith("```"):
                lines = cypher_query.split('\n')
                cypher_query = '\n'.join(lines[1:-1]) if len(lines) > 2 else cypher_query
            
            cypher_query = cypher_query.strip()
            
            logger.info(f"Generated Cypher query: {cypher_query}")
            
            return cypher_query
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="CypherGenerator",
                operation="generate_cypher",
                query=query
            )
            # Return None on error (graceful degradation)
            return None
