"""
Graph transformation module for converting text to knowledge graphs.

This module uses LLM to extract entities and relationships from text chunks
and convert them into graph documents for Neo4j storage.
"""

from typing import List
from langchain_core.documents import Document
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI

from src.utils.logger import setup_logger, log_error_with_context, log_llm_call
import time

logger = setup_logger(__name__)


class GraphTransformer:
    """
    Transforms text chunks into graph documents.
    
    This class uses an LLM to:
    - Extract entities (people, organizations, locations, etc.)
    - Identify relationships between entities
    - Convert extracted information into graph format
    - Maintain references to source chunks
    
    Attributes:
        llm: ChatOpenAI instance for entity extraction
        transformer: LLMGraphTransformer instance
        allowed_nodes: List of allowed node types
        allowed_relationships: List of allowed relationship types
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-nano",
        allowed_nodes: List[str] = None,
        allowed_relationships: List[str] = None
    ):
        """
        Initialize with LLM and schema constraints.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model name (default: "gpt-4o-mini")
            allowed_nodes: List of allowed node types. If None, uses default set.
            allowed_relationships: List of allowed relationship types. If None, uses default set.
        """
        logger.info(f"Initializing GraphTransformer with model='{model}'")
        
        # Set default allowed node types if not provided
        if allowed_nodes is None:
            allowed_nodes = [
                "Person",
                "Organization",
                "Location",
                "Event",
                "Product",
                "Technology",
                "Concept"
            ]
        
        # Set default allowed relationship types if not provided
        if allowed_relationships is None:
            allowed_relationships = [
                "WORKS_FOR",
                "LOCATED_IN",
                "PART_OF",
                "RELATED_TO",
                "OWNS",
                "MANAGES",
                "CREATED",
                "USES",
                "CONNECTED_TO"
            ]
        
        self.allowed_nodes = allowed_nodes
        self.allowed_relationships = allowed_relationships
        
        logger.info(f"Allowed node types: {', '.join(allowed_nodes)}")
        logger.info(f"Allowed relationship types: {', '.join(allowed_relationships)}")
        
        try:
            # Initialize OpenAI LLM
            self.llm = ChatOpenAI(
                api_key=api_key,
                model=model,
                temperature=0  # Use deterministic output for entity extraction
            )
            
            # Initialize LLMGraphTransformer
            self.transformer = LLMGraphTransformer(
                llm=self.llm,
                allowed_nodes=allowed_nodes,
                allowed_relationships=allowed_relationships,
                node_properties=["description"],  # Extract descriptions for nodes
                relationship_properties=["description"]  # Extract descriptions for relationships
            )
            
            logger.info("GraphTransformer initialized successfully")
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="GraphTransformer",
                operation="initialization",
                model=model
            )
            raise
    
    def transform_documents(self, chunks: List[Document]) -> List:
        """
        Extract entities and relationships from chunks.
        
        This method:
        1. Processes each chunk with the LLM
        2. Extracts entities and relationships
        3. Adds source_chunk_id reference to each node
        4. Handles errors gracefully (logs and continues)
        
        Args:
            chunks: List of text chunks to process
            
        Returns:
            List: List of GraphDocument objects with nodes and relationships.
                 Each node has a 'source_chunk_id' property linking to the original chunk.
            
        Example:
            >>> transformer = GraphTransformer(api_key="sk-...")
            >>> chunks = [Document(page_content="John works at OpenAI", metadata={"chunk_id": "123"})]
            >>> graph_docs = transformer.transform_documents(chunks)
            >>> print(f"Extracted {len(graph_docs)} graph documents")
        """
        if not chunks:
            logger.warning("No chunks provided to transform_documents")
            return []
        
        logger.info(f"Transforming {len(chunks)} chunks into graph documents")
        
        all_graph_docs = []
        successful = 0
        failed = 0
        
        for i, chunk in enumerate(chunks):
            try:
                # Get chunk_id from metadata
                chunk_id = chunk.metadata.get("chunk_id", f"chunk_{i}")
                
                logger.debug(f"Processing chunk {i+1}/{len(chunks)} (ID: {chunk_id})")
                
                # Track time for LLM call
                start_time = time.time()
                
                # Transform chunk to graph documents
                graph_docs = self.transformer.convert_to_graph_documents([chunk])
                
                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Log LLM call (approximate token counts)
                # Note: Actual token counts would require tracking from OpenAI response
                log_llm_call(
                    logger,
                    model=self.llm.model_name,
                    prompt_tokens=len(chunk.page_content) // 4,  # Rough estimate
                    completion_tokens=100,  # Rough estimate
                    total_tokens=(len(chunk.page_content) // 4) + 100,
                    latency_ms=latency_ms
                )
                
                # Add source_chunk_id to all nodes in the graph documents
                for graph_doc in graph_docs:
                    for node in graph_doc.nodes:
                        # Add source reference to node properties
                        if not hasattr(node, 'properties'):
                            node.properties = {}
                        node.properties['source_chunk_id'] = chunk_id
                
                all_graph_docs.extend(graph_docs)
                successful += 1
                
                logger.debug(
                    f"Extracted {len(graph_docs)} graph documents from chunk {chunk_id}"
                )
            
            except Exception as e:
                log_error_with_context(
                    logger,
                    e,
                    component="GraphTransformer",
                    operation="transform_chunk",
                    chunk_index=i,
                    chunk_id=chunk.metadata.get("chunk_id", "unknown")
                )
                failed += 1
                # Continue processing remaining chunks (graceful degradation)
                continue
        
        logger.info(
            f"Graph transformation complete: {successful} successful, {failed} failed. "
            f"Total graph documents: {len(all_graph_docs)}"
        )
        
        return all_graph_docs
    
    def extract_entities_only(self, text: str) -> List[dict]:
        """
        Extract only entities from text (without relationships).
        
        This is a simpler operation useful for quick entity extraction.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List[dict]: List of entity dictionaries with 'type' and 'name' keys
        """
        try:
            # Create a temporary document
            doc = Document(page_content=text, metadata={})
            
            # Transform to graph
            graph_docs = self.transformer.convert_to_graph_documents([doc])
            
            # Extract entities
            entities = []
            for graph_doc in graph_docs:
                for node in graph_doc.nodes:
                    entities.append({
                        "type": node.type,
                        "name": node.id,
                        "properties": getattr(node, 'properties', {})
                    })
            
            return entities
        
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                component="GraphTransformer",
                operation="extract_entities_only"
            )
            return []
