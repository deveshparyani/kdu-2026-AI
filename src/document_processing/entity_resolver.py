"""
Entity resolution module for merging duplicate entities in knowledge graphs.

This module provides functionality to normalize entity names and merge
duplicate entities based on similarity scoring.
"""

import re
from typing import List, Dict, Set
from difflib import SequenceMatcher

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class EntityResolver:
    """
    Resolves duplicate entities in knowledge graph.
    
    This class:
    - Normalizes entity names (lowercase, remove punctuation)
    - Calculates similarity between entities
    - Merges duplicate entities above threshold
    - Preserves all relationships during merging
    
    Attributes:
        similarity_threshold: Minimum similarity score for merging (0-1)
        alias_map: Dictionary mapping aliases to canonical names
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize with similarity threshold.
        
        Args:
            similarity_threshold: Minimum similarity score for merging (0-1).
                                 Default is 0.85 (85% similar).
        """
        self.similarity_threshold = similarity_threshold
        self.alias_map = {}  # Maps aliases to canonical entity names
        
        logger.info(f"EntityResolver initialized with threshold={similarity_threshold}")
    
    def normalize_entity_name(self, name: str) -> str:
        """
        Normalize entity name for comparison.
        
        This method:
        1. Converts to lowercase
        2. Removes punctuation
        3. Removes extra whitespace
        4. Applies alias mapping if available
        
        Args:
            name: Raw entity name
            
        Returns:
            str: Normalized name (lowercase, no punctuation, trimmed)
            
        Example:
            >>> resolver = EntityResolver()
            >>> resolver.normalize_entity_name("Apple Inc.")
            'apple inc'
            >>> resolver.normalize_entity_name("  John  Smith!  ")
            'john smith'
        """
        if not name:
            return ""
        
        # Step 1: Convert to lowercase
        normalized = name.lower()
        
        # Step 2: Remove punctuation (keep spaces and alphanumeric)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Step 3: Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Step 4: Apply alias mapping if exists
        if normalized in self.alias_map:
            normalized = self.alias_map[normalized]
        
        return normalized
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between normalized entity names.
        
        Uses SequenceMatcher for string similarity (similar to Levenshtein distance).
        The similarity score is between 0 (completely different) and 1 (identical).
        
        Args:
            name1: First entity name
            name2: Second entity name
            
        Returns:
            float: Similarity score between 0 and 1
            
        Example:
            >>> resolver = EntityResolver()
            >>> resolver.calculate_similarity("Apple Inc", "Apple Incorporated")
            0.87
            >>> resolver.calculate_similarity("John Smith", "Jane Doe")
            0.25
        """
        # Normalize both names first
        norm1 = self.normalize_entity_name(name1)
        norm2 = self.normalize_entity_name(name2)
        
        # Handle empty strings
        if not norm1 or not norm2:
            return 0.0
        
        # Handle identical names
        if norm1 == norm2:
            return 1.0
        
        # Calculate similarity using SequenceMatcher
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        return similarity
    
    def add_alias(self, alias: str, canonical_name: str) -> None:
        """
        Add an alias mapping for entity resolution.
        
        This allows you to specify that certain names should be treated
        as the same entity (e.g., "Apple" -> "Apple Inc").
        
        Args:
            alias: Alternative name for the entity
            canonical_name: The canonical (preferred) name
            
        Example:
            >>> resolver = EntityResolver()
            >>> resolver.add_alias("Apple", "Apple Inc")
            >>> resolver.normalize_entity_name("Apple")
            'apple inc'
        """
        normalized_alias = alias.lower().strip()
        normalized_canonical = canonical_name.lower().strip()
        
        self.alias_map[normalized_alias] = normalized_canonical
        logger.debug(f"Added alias mapping: '{alias}' -> '{canonical_name}'")
    
    def resolve_entities(self, graph_docs: List) -> List:
        """
        Merge duplicate entities across graph documents.
        
        This method:
        1. Collects all entities from all graph documents
        2. Groups similar entities (above threshold)
        3. Merges duplicate entities
        4. Preserves all relationships
        5. Logs merged entities
        
        Args:
            graph_docs: List of graph documents with nodes and relationships
            
        Returns:
            List: List of graph documents with merged entities
            
        Note:
            This modifies the graph documents in place and also returns them.
        """
        if not graph_docs:
            logger.warning("No graph documents provided to resolve_entities")
            return []
        
        logger.info(f"Resolving entities across {len(graph_docs)} graph documents")
        
        # Step 1: Collect all unique entities
        entity_map = {}  # Maps normalized name to list of (graph_doc_index, node_index, node)
        
        for doc_idx, graph_doc in enumerate(graph_docs):
            for node_idx, node in enumerate(graph_doc.nodes):
                normalized_name = self.normalize_entity_name(node.id)
                
                if normalized_name not in entity_map:
                    entity_map[normalized_name] = []
                
                entity_map[normalized_name].append((doc_idx, node_idx, node))
        
        logger.debug(f"Found {len(entity_map)} unique normalized entity names")
        
        # Step 2: Find similar entities and create merge groups
        merge_groups = []  # List of sets of normalized names to merge
        processed = set()
        
        entity_names = list(entity_map.keys())
        for i, name1 in enumerate(entity_names):
            if name1 in processed:
                continue
            
            # Start a new merge group
            merge_group = {name1}
            
            # Find all similar entities
            for name2 in entity_names[i+1:]:
                if name2 in processed:
                    continue
                
                # Calculate similarity
                similarity = self.calculate_similarity(name1, name2)
                
                if similarity >= self.similarity_threshold:
                    merge_group.add(name2)
                    processed.add(name2)
            
            if len(merge_group) > 1:
                merge_groups.append(merge_group)
                logger.info(f"Found merge group: {merge_group}")
            
            processed.add(name1)
        
        logger.info(f"Found {len(merge_groups)} groups of entities to merge")
        
        # Step 3: Merge entities in each group
        for merge_group in merge_groups:
            # Choose canonical name (shortest one, or first alphabetically if tie)
            canonical_name = min(merge_group, key=lambda x: (len(x), x))
            
            logger.info(f"Merging entities into canonical name: '{canonical_name}'")
            logger.info(f"Merging: {', '.join(merge_group)}")
            
            # Get canonical node (from first occurrence)
            canonical_entities = entity_map[canonical_name]
            canonical_doc_idx, canonical_node_idx, canonical_node = canonical_entities[0]
            
            # Merge all other entities into canonical
            for name in merge_group:
                if name == canonical_name:
                    continue
                
                # Get all occurrences of this entity
                entities_to_merge = entity_map[name]
                
                for doc_idx, node_idx, node in entities_to_merge:
                    # Update node ID to canonical name
                    graph_docs[doc_idx].nodes[node_idx].id = canonical_node.id
                    
                    # Merge properties (keep all unique properties)
                    if hasattr(node, 'properties') and hasattr(canonical_node, 'properties'):
                        for key, value in node.properties.items():
                            if key not in canonical_node.properties:
                                canonical_node.properties[key] = value
                    
                    # Update relationships that reference this node
                    for rel in graph_docs[doc_idx].relationships:
                        if rel.source.id == node.id:
                            rel.source = canonical_node
                        if rel.target.id == node.id:
                            rel.target = canonical_node
        
        logger.info("Entity resolution complete")
        
        return graph_docs
    
    def get_entity_stats(self, graph_docs: List) -> Dict:
        """
        Get statistics about entities in graph documents.
        
        Args:
            graph_docs: List of graph documents
            
        Returns:
            Dict: Statistics including:
                - total_entities: Total number of entity nodes
                - unique_entities: Number of unique entity names
                - entity_types: Count of each entity type
        """
        if not graph_docs:
            return {
                "total_entities": 0,
                "unique_entities": 0,
                "entity_types": {}
            }
        
        all_entities = []
        unique_names = set()
        entity_types = {}
        
        for graph_doc in graph_docs:
            for node in graph_doc.nodes:
                all_entities.append(node)
                unique_names.add(self.normalize_entity_name(node.id))
                
                # Count entity types
                entity_type = node.type
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        return {
            "total_entities": len(all_entities),
            "unique_entities": len(unique_names),
            "entity_types": entity_types
        }
