"""Verifica o índice persistente contra o corpus declarado no manifesto."""

from collections import Counter

import chromadb

from src.rag.chunking import chunk_documents
from src.rag.loader import DEFAULT_MANIFEST, load_corpus
from src.rag.vector_store import DEFAULT_COLLECTION, DEFAULT_INDEX, corpus_fingerprint


def main():
    documents = load_corpus(DEFAULT_MANIFEST)
    expected = chunk_documents(documents)
    collection = chromadb.PersistentClient(path=str(DEFAULT_INDEX)).get_collection(DEFAULT_COLLECTION)
    records = collection.get(include=["documents", "metadatas"])
    ids = records["ids"]
    assert collection.count() == len(ids) == len(expected)
    assert len(ids) == len(set(ids))
    assert len(records["documents"]) == len(set(records["documents"]))
    assert set(ids) == {doc.metadata["chunk_id"] for doc in expected}
    expected_by_id = {doc.metadata["chunk_id"]: doc for doc in expected}
    for id_, text, metadata in zip(ids, records["documents"], records["metadatas"]):
        original = expected_by_id[id_]
        assert text == original.page_content
        for key in ("source", "document", "section", "version", "date", "type", "authority", "corpus_path"):
            assert metadata[key] == original.metadata[key], (id_, key)
        assert metadata["page"] == (original.metadata["page"] or 0)
        assert metadata["characters"] == len(text)
    version = collection.metadata or {}
    assert version["fingerprint"] == corpus_fingerprint(expected, version["embedding_model"],
                                                         version["chunk_size"], version["chunk_overlap"])
    sections = sorted({doc.metadata["section"] for doc in documents})
    pages = Counter("sem página" if doc.metadata["page"] is None else str(doc.metadata["page"])
                    for doc in documents)
    print(f"documents={len(documents)} chunks={len(ids)} unique_ids={len(set(ids))} "
          f"unique_texts={len(set(records['documents']))} sections={len(sections)} pages={dict(pages)}")
    for section in sections:
        print(f"section={section}")


if __name__ == "__main__":
    main()
