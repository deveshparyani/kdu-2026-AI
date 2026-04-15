from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source: str
    collection_name: str | None = None
    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=100, ge=0)
    persist_directory: str = "storage/chroma"


class IngestResponse(BaseModel):
    source: str
    collection_name: str
    loaded_documents: int
    cleaned_documents: int
    chunks_created: int
    chroma_collection: str
    persist_directory: str
    chunks_file_path: str


class RetrieveRequest(BaseModel):
    query: str
    collection_name: str
    persist_directory: str = "storage/chroma"
    chunks_directory: str = "storage/chunks"
    semantic_k: int = Field(default=4, gt=0)
    keyword_k: int = Field(default=4, gt=0)
    final_k: int = Field(default=6, gt=0)


class AskRequest(BaseModel):
    query: str
    collection_name: str
    persist_directory: str = "storage/chroma"
    chunks_directory: str = "storage/chunks"
    semantic_k: int = Field(default=4, gt=0)
    keyword_k: int = Field(default=4, gt=0)
    final_k: int = Field(default=6, gt=0)
    model_name: str | None = None
