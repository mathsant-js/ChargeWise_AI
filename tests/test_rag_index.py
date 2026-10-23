import sys
import types

import pytest
from langchain_core.documents import Document

from src.rag.chunking import chunk_documents
from src.rag.vector_store import corpus_fingerprint, index_corpus


def test_chunking_keeps_provenance_and_stable_ids():
    source = Document(page_content="A " * 700, metadata={
        "source": "fonte", "document": "Documento", "section": "Seção",
        "page": 2, "corpus_path": "manual.pdf",
    })
    chunks = chunk_documents([source])
    assert len(chunks) > 1
    assert [x.metadata["chunk_id"] for x in chunks] == [x.metadata["chunk_id"] for x in chunk_documents([source])]
    assert all(x.metadata["source"] == "fonte" and x.metadata["page"] == 2 for x in chunks)
    assert all(x.metadata["characters"] <= 900 and x.metadata["tokens_cl100k_base"] >= -1 for x in chunks)


def test_bad_chunk_configuration():
    with pytest.raises(ValueError):
        chunk_documents([], chunk_size=100, chunk_overlap=100)


def test_metadata_change_invalidates_fingerprint():
    original = Document(page_content="Tarifa: R$ 0,92", metadata={
        "chunk_id": "stable", "source": "origem.md", "document": "Cenário",
        "section": "Tarifa", "page": None, "authority": "simulado",
    })
    corrected = original.model_copy(deep=True)
    corrected.metadata["source"] = "fonte-corrigida.md"
    assert corpus_fingerprint([original], "nomic-embed-text", 900, 135) != corpus_fingerprint(
        [corrected], "nomic-embed-text", 900, 135
    )


def test_repeated_ingestion_does_not_duplicate(tmp_path, monkeypatch):
    from src.rag import vector_store

    class Collection:
        def __init__(self, metadata):
            self.metadata = metadata
            self.ids = []

        def count(self):
            return len(self.ids)

        def add(self, ids, documents, metadatas, embeddings):
            assert all(None not in metadata.values() for metadata in metadatas)
            self.ids.extend(ids)

    class Client:
        collection = None

        def get_collection(self, name):
            if self.collection is None:
                raise ValueError("missing")
            return self.collection

        def create_collection(self, name, metadata):
            self.collection = Collection(metadata)
            return self.collection

        def delete_collection(self, name):
            self.collection = None

    client = Client()
    fake_chroma = types.SimpleNamespace(PersistentClient=lambda path: client, errors=types.SimpleNamespace(NotFoundError=ValueError))
    monkeypatch.setitem(sys.modules, "chromadb", fake_chroma)
    monkeypatch.setattr(vector_store, "load_corpus", lambda path: [Document(page_content="Texto de teste", metadata={
        "source": "fonte", "document": "Documento", "section": "Seção", "page": None,
    })])

    class Embeddings:
        model = "teste"
        calls = 0

        def embed_documents(self, texts):
            self.calls += 1
            return [[0.1, 0.2] for _ in texts]

    embeddings = Embeddings()
    first = index_corpus(persist_directory=tmp_path, embeddings=embeddings)
    second = index_corpus(persist_directory=tmp_path, embeddings=embeddings)
    assert first["status"] == "indexed"
    assert second["status"] == "unchanged"
    assert embeddings.calls == 1
    assert client.collection.count() == 1
