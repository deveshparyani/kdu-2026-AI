"""
Main entry point for the Hybrid GraphRAG Chatbot.

This module provides a CLI interface for:
- Ingesting PDF documents
- Querying the knowledge base
- Comparing traditional RAG vs GraphRAG
"""

import sys
import argparse
from pathlib import Path

# Import configuration
from src.config import Config
from src.utils.logger import setup_logger, create_user_friendly_error

# Import document processing
from src.document_processing.pdf_loader import PDFLoader
from src.document_processing.text_chunker import TextChunker
from src.document_processing.graph_transformer import GraphTransformer
from src.document_processing.entity_resolver import EntityResolver

# Import storage
from src.storage.vector_store import VectorStore
from src.storage.graph_store import GraphStore

# Import retrieval
from src.retrieval.query_decomposer import QueryDecomposer
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.cypher_generator import CypherGenerator
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.rrf_reranker import RRFReranker

# Import generation
from src.generation.answer_generator import AnswerGenerator

logger = setup_logger(__name__)


class HybridGraphRAGChatbot:
    """
    Main chatbot class that orchestrates all components.
    
    This class:
    - Manages document ingestion pipeline
    - Handles query processing pipeline
    - Provides comparison mode
    """
    
    def __init__(self, config: Config):
        """
        Initialize chatbot with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        logger.info("Initializing Hybrid GraphRAG Chatbot")
        
        # Initialize storage
        self.vector_store = VectorStore(
            embedding_model=config.embedding_model
        )
        
        self.graph_store = GraphStore(
            uri=config.neo4j_uri,
            username=config.neo4j_username,
            password=config.neo4j_password,
            database=config.neo4j_database
        )
        
        # Initialize document processing
        self.pdf_loader = PDFLoader(max_size_mb=config.max_pdf_size_mb)
        self.text_chunker = TextChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
        self.graph_transformer = GraphTransformer(
            api_key=config.openai_api_key,
            model=config.openai_model
        )
        self.entity_resolver = EntityResolver(
            similarity_threshold=config.entity_similarity_threshold
        )
        
        # Initialize retrieval (will be set up after documents are loaded)
        self.bm25_retriever = None
        self.query_decomposer = QueryDecomposer(
            api_key=config.openai_api_key,
            model=config.openai_model
        )
        self.cypher_generator = CypherGenerator(
            api_key=config.openai_api_key,
            graph_store=self.graph_store,
            model=config.openai_model
        )
        self.hybrid_retriever = None
        self.rrf_reranker = RRFReranker(k=config.rrf_constant)
        
        # Initialize generation
        self.answer_generator = AnswerGenerator(
            api_key=config.openai_api_key,
            model=config.openai_model,
            timeout=config.answer_timeout
        )
        
        logger.info("Chatbot initialized successfully")
    
    def ingest_document(self, pdf_path: str) -> None:
        """
        Ingest a PDF document into the system.
        
        This method:
        1. Loads PDF and extracts text
        2. Chunks text
        3. Stores chunks in vector store
        4. Transforms chunks to graph
        5. Resolves entities
        6. Stores graph in Neo4j
        
        Args:
            pdf_path: Path to PDF file
        """
        logger.info(f"Starting document ingestion for: {pdf_path}")
        
        try:
            # Step 1: Load PDF
            print(f"\n📄 Loading PDF: {pdf_path}")
            documents = self.pdf_loader.load(pdf_path)
            print(f"✓ Loaded {len(documents)} pages")
            
            # Step 2: Chunk text
            print(f"\n✂️  Chunking text...")
            chunks = self.text_chunker.chunk_documents(documents)
            print(f"✓ Created {len(chunks)} chunks")
            
            # Step 3: Store in vector store
            print(f"\n💾 Storing chunks in vector database...")
            self.vector_store.add_documents(chunks)
            print(f"✓ Stored {len(chunks)} chunks with embeddings")
            
            # Step 4: Transform to graph
            print(f"\n🕸️  Extracting entities and relationships...")
            graph_docs = self.graph_transformer.transform_documents(chunks)
            print(f"✓ Extracted {len(graph_docs)} graph documents")
            
            # Step 5: Resolve entities
            print(f"\n🔗 Resolving duplicate entities...")
            resolved_graph_docs = self.entity_resolver.resolve_entities(graph_docs)
            stats = self.entity_resolver.get_entity_stats(resolved_graph_docs)
            print(f"✓ Resolved to {stats['unique_entities']} unique entities")
            
            # Step 6: Store in graph database
            print(f"\n🗄️  Storing graph in Neo4j...")
            self.graph_store.add_graph_documents(resolved_graph_docs)
            print(f"✓ Stored graph with {stats['total_entities']} nodes")
            
            # Step 7: Initialize BM25 retriever with all documents
            print(f"\n🔍 Initializing BM25 retriever...")
            all_docs = self.vector_store.get_all_documents()
            self.bm25_retriever = BM25Retriever(all_docs)
            print(f"✓ BM25 index created")
            
            # Step 8: Initialize hybrid retriever
            self.hybrid_retriever = HybridRetriever(
                bm25_retriever=self.bm25_retriever,
                vector_store=self.vector_store,
                cypher_generator=self.cypher_generator,
                graph_store=self.graph_store
            )
            
            print(f"\n✅ Document ingestion complete!")
            print(f"   - {len(chunks)} chunks indexed")
            print(f"   - {stats['unique_entities']} unique entities")
            print(f"   - Ready for queries")
        
        except Exception as e:
            error_msg = create_user_friendly_error(e, "ingesting document")
            print(f"\n❌ Error: {error_msg}")
            logger.error(f"Document ingestion failed: {str(e)}")
            raise
    
    def query(self, question: str) -> dict:
        """
        Query the knowledge base.
        
        This method:
        1. Decomposes query if complex
        2. Retrieves relevant chunks using hybrid search
        3. Reranks results using RRF
        4. Generates answer using LLM
        
        Args:
            question: User question
            
        Returns:
            dict: Answer with sources and metadata
        """
        if not self.hybrid_retriever:
            raise ValueError(
                "No documents have been ingested yet. "
                "Please ingest a document first using the 'ingest' command."
            )
        
        logger.info(f"Processing query: {question}")
        
        try:
            # Step 1: Decompose query
            print(f"\n🔍 Analyzing query...")
            sub_queries = self.query_decomposer.decompose(question)
            
            if len(sub_queries) > 1:
                print(f"✓ Decomposed into {len(sub_queries)} sub-queries")
                for i, sq in enumerate(sub_queries, 1):
                    print(f"   {i}. {sq}")
            else:
                print(f"✓ Query is simple, no decomposition needed")
            
            # Step 2: Retrieve for each sub-query
            print(f"\n🔎 Retrieving relevant information...")
            all_results = {}
            
            for sq in sub_queries:
                results = self.hybrid_retriever.retrieve(sq, k=self.config.top_k_results)
                
                # Merge results
                for method, method_results in results.items():
                    if method not in all_results:
                        all_results[method] = []
                    all_results[method].extend(method_results)
            
            total_results = sum(len(r) for r in all_results.values())
            print(f"✓ Retrieved {total_results} results")
            print(f"   - BM25: {len(all_results.get('bm25', []))} results")
            print(f"   - Semantic: {len(all_results.get('semantic', []))} results")
            print(f"   - Graph: {len(all_results.get('graph', []))} results")
            
            # Step 3: Rerank using RRF
            print(f"\n📊 Reranking results...")
            reranked = self.rrf_reranker.rerank(all_results, top_k=self.config.top_k_results)
            print(f"✓ Selected top {len(reranked)} results")
            
            # Step 4: Generate answer
            print(f"\n💭 Generating answer...")
            result = self.answer_generator.generate_answer(question, reranked)
            print(f"✓ Answer generated in {result['latency_ms']}ms")
            
            return result
        
        except Exception as e:
            error_msg = create_user_friendly_error(e, "processing query")
            print(f"\n❌ Error: {error_msg}")
            logger.error(f"Query processing failed: {str(e)}")
            raise


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Hybrid GraphRAG Chatbot - Multi-hop reasoning over PDF documents"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a PDF document")
    ingest_parser.add_argument("pdf_path", help="Path to PDF file")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query the knowledge base")
    query_parser.add_argument("question", help="Question to ask")
    
    # Interactive command
    subparsers.add_parser("interactive", help="Start interactive query mode")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Load configuration
        print("🚀 Initializing Hybrid GraphRAG Chatbot...")
        config = Config.from_env()
        chatbot = HybridGraphRAGChatbot(config)
        print("✓ Chatbot initialized\n")
        
        if args.command == "ingest":
            chatbot.ingest_document(args.pdf_path)
        
        elif args.command == "query":
            result = chatbot.query(args.question)
            
            print(f"\n{'='*80}")
            print(f"ANSWER:")
            print(f"{'='*80}")
            print(result['answer'])
            print(f"\n{'='*80}")
            print(f"SOURCES: {result['num_sources']} documents used")
            print(f"{'='*80}\n")
        
        elif args.command == "interactive":
            print("📝 Interactive mode - Type 'exit' to quit\n")
            
            while True:
                try:
                    question = input("\n❓ Your question: ").strip()
                    
                    if question.lower() in ['exit', 'quit', 'q']:
                        print("\n👋 Goodbye!")
                        break
                    
                    if not question:
                        continue
                    
                    result = chatbot.query(question)
                    
                    print(f"\n{'='*80}")
                    print(f"💡 ANSWER:")
                    print(f"{'='*80}")
                    print(result['answer'])
                    print(f"\n📚 Used {result['num_sources']} sources")
                    print(f"{'='*80}")
                
                except KeyboardInterrupt:
                    print("\n\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {str(e)}")
                    continue
    
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
