import json

import pytest
from langchain_core.documents import Document

from src.rag.loader import clean_text, load_corpus


def test_corpus_preserves_sections_and_simulated_provenance():
    docs = load_corpus()
    assert any(
        "Tarifa padrão: R$0,92/kWh" in doc.page_content
        and doc.metadata["section"].endswith("Tarifa Padrão")
        and doc.metadata["source"] == "data/conhecimento_condominio_v2.md"
        and doc.metadata["authority"] == "simulado"
        and doc.metadata["page"] is None
        for doc in docs
    )
    assert all(doc.metadata["section"] and doc.metadata["document"] for doc in docs)


def test_clean_text_removes_pdf_noise_conservatively():
    assert clean_text("Eletro-\nposto\ufeff\r\n\r\n\r\nTarifa  R$ 0,92") == "Eletroposto\n\nTarifa R$ 0,92"


def test_manifest_rejects_path_outside_corpus(tmp_path):
    manifest = {"schema_version": 1, "documents": [{
        "path": "../outside.md", "document": "x", "source": "x", "origin": "x",
        "version": "1", "date": "2026-10-23", "type": "x", "authority": "x", "sections": []
    }]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Caminho inválido"):
        load_corpus(path)


def test_pdf_page_number_is_one_based(tmp_path, monkeypatch):
    import langchain_community.document_loaders as loaders

    class FakePDFLoader:
        def __init__(self, file_path, mode):
            assert mode == "page"

        def load(self):
            return [Document(page_content="Página 2\n\nConteúdo", metadata={"page": 1})]

    monkeypatch.setattr(loaders, "PyMuPDFLoader", FakePDFLoader)
    (tmp_path / "manual.pdf").write_bytes(b"%PDF-placeholder")
    entry = {"path": "manual.pdf", "document": "Manual", "source": "fornecedor", "origin": "teste",
             "version": "1", "date": "2026-10-23", "type": "manual", "authority": "oficial", "sections": []}
    (tmp_path / "manifest.json").write_text(json.dumps({"schema_version": 1, "documents": [entry]}), encoding="utf-8")
    docs = load_corpus(tmp_path / "manifest.json")
    assert docs[0].metadata["page"] == 2
    assert docs[0].metadata["section"] == "Página 2"
