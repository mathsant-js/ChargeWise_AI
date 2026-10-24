"""Divide seções do corpus sem perder sua proveniência."""

from __future__ import annotations

import hashlib

import tiktoken
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(documents: list[Document], chunk_size: int = 900, chunk_overlap: int = 135) -> list[Document]:
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_size deve ser positivo e overlap menor que chunk_size")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    try:
        encoder = tiktoken.get_encoding("cl100k_base")
    except (OSError, ImportError, ConnectionError):
        encoder = None
    result: list[Document] = []
    for document in documents:
        if all(line.lstrip().startswith("#") for line in document.page_content.splitlines() if line.strip()):
            continue
        for ordinal, text in enumerate(splitter.split_text(document.page_content)):
            identity = "\x1f".join(str(x) for x in (
                document.metadata.get("corpus_path", document.metadata.get("source", "")),
                document.metadata.get("section", ""), document.metadata.get("page"), ordinal, text,
            ))
            chunk_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            result.append(Document(page_content=text, metadata={
                **document.metadata, "chunk_id": chunk_id,
                "chunk_ordinal": ordinal, "characters": len(text),
                "tokens_cl100k_base": len(encoder.encode(text)) if encoder else -1,
            }))
    return result
