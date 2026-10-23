"""Carrega o corpus declarado no manifesto, preservando origem e seções."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from langchain_core.documents import Document

DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / "data/knowledge_base/manifest.json"
_REQUIRED = {"path", "document", "source", "origin", "version", "date", "type", "authority", "sections"}


def clean_text(text: str) -> str:
    """Retira ruído de extração sem apagar pontuação ou conteúdo substantivo."""
    text = text.replace("\ufeff", "").replace("\u00ad", "")
    text = re.sub(r"[\x00-\x08\x0b\x0e-\x1f\x7f]", "", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _markdown_sections(text: str):
    heading_path: list[str] = []
    lines: list[str] = []
    section = "Introdução"

    def flush():
        content = clean_text("\n".join(lines))
        if content:
            yield section, content

    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            yield from flush()
            level = len(match.group(1))
            heading_path = heading_path[: level - 1] + [match.group(2).strip()]
            section = " / ".join(heading_path)
            lines = [line]
        else:
            lines.append(line)
    yield from flush()


def load_corpus(manifest_path: str | Path = DEFAULT_MANIFEST) -> list[Document]:
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("documents"), list):
        raise ValueError("Manifesto inválido: schema_version=1 e documents são obrigatórios")
    documents: list[Document] = []
    seen: set[str] = set()
    base = manifest_path.parent
    for entry in manifest["documents"]:
        missing = _REQUIRED - entry.keys()
        if missing:
            raise ValueError(f"Metadados ausentes: {sorted(missing)}")
        relative = Path(entry["path"])
        path = (base / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(base) or not path.is_file():
            raise ValueError(f"Caminho inválido ou ausente no corpus: {relative}")
        if str(relative) in seen:
            raise ValueError(f"Documento duplicado no manifesto: {relative}")
        seen.add(str(relative))
        metadata = {key: entry[key] for key in ("document", "source", "origin", "version", "date", "type", "authority")}
        metadata["corpus_path"] = str(relative)
        if path.suffix.lower() == ".md":
            for section, content in _markdown_sections(path.read_text(encoding="utf-8")):
                documents.append(Document(page_content=content, metadata={**metadata, "section": section, "page": None}))
        elif path.suffix.lower() == ".pdf":
            try:
                from langchain_community.document_loaders import PyMuPDFLoader
                pages = PyMuPDFLoader(str(path), mode="page").load()
            except ImportError as exc:
                raise RuntimeError("Para PDFs, instale as dependências de requirements.txt (PyMuPDF).") from exc
            for page in pages:
                number = int(page.metadata.get("page", 0)) + 1
                content = clean_text(page.page_content)
                if content:
                    documents.append(Document(page_content=content, metadata={**metadata, "section": f"Página {number}", "page": number}))
        else:
            raise ValueError(f"Formato não suportado: {relative}")
    return documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspeciona o corpus RAG, sem criar índice")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = parser.parse_args()
    for doc in load_corpus(args.manifest):
        print(json.dumps({"metadata": doc.metadata, "characters": len(doc.page_content)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
