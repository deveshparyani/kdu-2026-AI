import os
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("USER_AGENT", "kdu-ai-rag/0.1")

from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_core.documents import Document


def is_url(value: str) -> bool:
    """Return True when the input looks like a web URL."""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_pdf(file_path: str | Path) -> list[Document]:
    """Load a PDF file and return the extracted documents."""
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"PDF file not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("File must be a PDF.")

    loader = PyPDFLoader(str(path))
    documents = loader.load()

    if not documents:
        raise ValueError("No text could be loaded from the PDF.")

    return documents


def load_url(url: str) -> list[Document]:
    """Load a web page or blog URL and return the extracted documents."""
    if not is_url(url):
        raise ValueError("Please provide a valid URL.")

    loader = WebBaseLoader(web_paths=[url])
    documents = loader.load()

    if not documents:
        raise ValueError("No text could be loaded from the URL.")

    return documents


def load_source(source: str | Path) -> list[Document]:
    """Load either a PDF path or a URL."""
    if isinstance(source, Path):
        return load_pdf(source)

    source_text = str(source).strip()

    if is_url(source_text):
        return load_url(source_text)

    return load_pdf(source_text)
