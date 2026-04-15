import argparse
from app.rag.generate_answer import answer_question
from app.rag.pipeline import index_source


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load a PDF or URL and store its chunks in Chroma."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="PDF file path or blog URL",
    )
    parser.add_argument(
        "--collection-name",
        default=None,
        help="Optional Chroma collection name",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=800,
        help="Chunk size for splitting text",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=100,
        help="Chunk overlap for splitting text",
    )
    parser.add_argument(
        "--persist-directory",
        default="storage/chroma",
        help="Directory where Chroma stores data locally",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Optional question to ask after indexing the source",
    )

    args = parser.parse_args()

    indexing_result = index_source(
        source=args.source,
        collection_name=args.collection_name,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        persist_directory=args.persist_directory,
    )
    final_collection_name = str(indexing_result["collection_name"])

    print(f"Source: {indexing_result['source']}")
    print(f"Collection name: {indexing_result['collection_name']}")
    print(f"Loaded documents: {indexing_result['loaded_documents']}")
    print(f"Cleaned documents: {indexing_result['cleaned_documents']}")
    print(f"Chunks created: {indexing_result['chunks_created']}")
    print(f"Chroma collection ready: {indexing_result['chroma_collection']}")
    print(f"Stored at: {indexing_result['persist_directory']}")
    print(f"BM25 chunks file: {indexing_result['chunks_file_path']}")

    if args.query:
        result = answer_question(
            query=args.query,
            collection_name=final_collection_name,
            persist_directory=args.persist_directory,
        )
        print("\nAnswer:")
        print(result["answer"])
        print("\nSources used:")
        for index, item in enumerate(result["sources"], start=1):
            metadata = item.get("metadata", {})
            source = metadata.get("source", "unknown") if isinstance(metadata, dict) else "unknown"
            score = metadata.get("hybrid_score", "n/a") if isinstance(metadata, dict) else "n/a"
            print(f"{index}. source={source} hybrid_score={score}")


if __name__ == "__main__":
    main()
