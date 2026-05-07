"""
Graph storage module using Neo4j for knowledge graph storage and querying.

This module provides functionality to store graph documents in Neo4j
and execute Cypher queries for graph-based retrieval.
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from langchain_community.graphs import Neo4jGraph

from src.utils.logger import setup_logger, log_error_with_context, create_user_friendly_error

logger = setup_logger(__name__)


class GraphStore:
    """
    Neo4j wrapper for graph storage and querying.
    
    This class handles:
    - Connecting to Neo4j database
    - Storing graph documents (nodes and relationships)
    - Executing Cypher queries
    - Retrieving graph schema
    - Graceful error handling
    
    Attributes:
        uri: Neo4j connection URI
        username: Neo4j username
        database: Neo4j database name
        driver: Neo4j driver instance
        graph: LangChain Neo4jGraph instance
    """
    
    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        database: str = "neo4j"
    ):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j connection URI (e.g., "neo4j+s://xxx.databases.neo4j.io")
            username: Neo4j username
            password: Neo4j password
            database: Neo4j database name (default: "neo4j")
            
        Raises:
            ConnectionError: If connection to Neo4j fails
        """
        self.uri = uri
        self.username = username
        self.database = database
        
        # Note: We don't log the password (credential security)
        logger.info(f"Initializing GraphStore connection to {uri}, database={database}")
        
        try:
            # Initialize Neo4j driver
            self.driver = GraphDatabase.driver(
                uri,
                auth=(username, password)
            )
            
            # Test connection
            with self.driver.session(database=database) as session:
                result = session.run("RETURN 1 AS test")
                result.single()
            
            logger.info("Successfully connected to Neo4j")
            
            # Initialize LangChain Neo4jGraph for easier operations
            self.graph = Neo4jGraph(
                url=uri,
                username=username,
                password=password,
                database=database
            )
            
            logger.info("Neo4jGraph initialized")
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="GraphStore",
                operation="initialization",
                uri=uri,
                database=database
            )
            user_msg = create_user_friendly_error(e, "connecting to Neo4j")
            raise ConnectionError(user_msg) from e
    
    def add_graph_documents(self, graph_docs: List) -> None:
        """
        Add graph documents to Neo4j.
        
        This method:
        1. Extracts nodes and relationships from graph documents
        2. Creates nodes in Neo4j with properties
        3. Creates relationships between nodes
        4. Handles errors gracefully
        
        Args:
            graph_docs: List of graph documents with nodes and relationships
            
        Example:
            >>> graph_store = GraphStore(uri="neo4j+s://...", username="neo4j", password="...")
            >>> graph_store.add_graph_documents(graph_docs)
            Successfully added 10 nodes and 15 relationships to Neo4j
        """
        if not graph_docs:
            logger.warning("No graph documents provided to add_graph_documents")
            return
        
        logger.info(f"Adding {len(graph_docs)} graph documents to Neo4j")
        
        total_nodes = 0
        total_relationships = 0
        
        try:
            # Use LangChain's add_graph_documents method
            self.graph.add_graph_documents(graph_docs)
            
            # Count nodes and relationships
            for graph_doc in graph_docs:
                total_nodes += len(graph_doc.nodes)
                total_relationships += len(graph_doc.relationships)
            
            logger.info(
                f"Successfully added {total_nodes} nodes and "
                f"{total_relationships} relationships to Neo4j"
            )
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="GraphStore",
                operation="add_graph_documents",
                num_docs=len(graph_docs)
            )
            raise
    
    def execute_cypher(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute Cypher query against Neo4j.
        
        This method:
        1. Executes the provided Cypher query
        2. Returns results as list of dictionaries
        3. Handles errors gracefully (logs and returns empty list)
        
        Args:
            query: Cypher query string
            parameters: Optional parameters for the query
            
        Returns:
            List[Dict[str, Any]]: List of result dictionaries.
                                 Each dict contains the query result fields.
            
        Raises:
            Exception: If query execution fails critically
            
        Example:
            >>> graph_store = GraphStore(...)
            >>> results = graph_store.execute_cypher(
            ...     "MATCH (p:Person)-[:WORKS_FOR]->(o:Organization) RETURN p.name, o.name"
            ... )
            >>> for result in results:
            ...     print(f"{result['p.name']} works for {result['o.name']}")
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to execute_cypher")
            return []
        
        if parameters is None:
            parameters = {}
        
        logger.debug(f"Executing Cypher query: {query[:200]}...")
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                
                # Convert result to list of dictionaries
                records = []
                for record in result:
                    records.append(dict(record))
                
                logger.info(f"Cypher query returned {len(records)} results")
                
                return records
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="GraphStore",
                operation="execute_cypher",
                query=query[:200]
            )
            # Return empty results on error (graceful degradation)
            return []
    
    def get_schema(self) -> str:
        """
        Get Neo4j graph schema for Cypher generation.
        
        This returns information about:
        - Node types (labels)
        - Relationship types
        - Properties on nodes and relationships
        
        Returns:
            str: String representation of graph schema
            
        Example:
            >>> graph_store = GraphStore(...)
            >>> schema = graph_store.get_schema()
            >>> print(schema)
            Node properties:
            Person {name: STRING, age: INTEGER}
            Organization {name: STRING}
            Relationship properties:
            WORKS_FOR {}
        """
        try:
            schema = self.graph.get_schema
            logger.debug("Retrieved graph schema")
            return schema
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="GraphStore",
                operation="get_schema"
            )
            return "Schema unavailable"
    
    def clear_database(self) -> None:
        """
        Clear all nodes and relationships from the database.
        
        Warning: This permanently deletes all data in the Neo4j database.
        Use with caution!
        """
        logger.warning("Clearing all data from Neo4j database")
        
        try:
            query = "MATCH (n) DETACH DELETE n"
            self.execute_cypher(query)
            logger.info("Successfully cleared Neo4j database")
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="GraphStore",
                operation="clear_database"
            )
            raise
    
    def get_node_count(self) -> int:
        """
        Get total number of nodes in the database.
        
        Returns:
            int: Number of nodes
        """
        try:
            query = "MATCH (n) RETURN count(n) AS count"
            results = self.execute_cypher(query)
            
            if results:
                return results[0]['count']
            return 0
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="GraphStore",
                operation="get_node_count"
            )
            return 0
    
    def get_relationship_count(self) -> int:
        """
        Get total number of relationships in the database.
        
        Returns:
            int: Number of relationships
        """
        try:
            query = "MATCH ()-[r]->() RETURN count(r) AS count"
            results = self.execute_cypher(query)
            
            if results:
                return results[0]['count']
            return 0
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="GraphStore",
                operation="get_relationship_count"
            )
            return 0
    
    def close(self) -> None:
        """
        Close the Neo4j connection.
        
        This should be called when done using the graph store
        to properly release resources.
        """
        try:
            if self.driver:
                self.driver.close()
                logger.info("Neo4j connection closed")
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="GraphStore",
                operation="close"
            )
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.close()
