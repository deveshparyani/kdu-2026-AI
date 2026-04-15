import re

from langchain_core.documents import Document


def clean_text(text: str) -> str:
    """Do light cleaning without changing the meaning of the text."""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_documents(documents: list[Document]) -> list[Document]:
    """Clean all loaded documents and keep their metadata."""
    cleaned_documents: list[Document] = []

    for document in documents:
        cleaned_text = clean_text(document.page_content)

        if not cleaned_text:
            continue

        cleaned_documents.append(
            Document(
                page_content=cleaned_text,
                metadata=document.metadata,
            )
        )

    return cleaned_documents
