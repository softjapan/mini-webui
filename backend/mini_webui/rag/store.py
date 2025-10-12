from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from langchain.schema import Document
from langchain_community.vectorstores.faiss import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import OPENAI_API_KEY, RAG_EMBEDDING_MODEL, RAG_LANGUAGE
from .preprocess import preprocess_markdown_tables

log = logging.getLogger("mini_webui.rag.store")


@dataclass
class VectorStoreManager:
    index_path: Path
    embedding_model: str = RAG_EMBEDDING_MODEL
    language: str = RAG_LANGUAGE
    chunk_size: int = 1024
    chunk_overlap: int = 128

    _vectorstore: Optional[FAISS] = None

    @property
    def embedding(self) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(model=self.embedding_model, api_key=OPENAI_API_KEY)

    def load(self) -> Optional[FAISS]:
        if self._vectorstore is not None:
            return self._vectorstore
        faiss_index = self.index_path / "index.faiss"
        docstore_path = self.index_path / "index.pkl"
        if faiss_index.exists() and docstore_path.exists():
            log.info("Loading FAISS index from %s", self.index_path)
            self._vectorstore = FAISS.load_local(
                str(self.index_path),
                self.embedding,
                allow_dangerous_deserialization=True,
            )
        return self._vectorstore

    def save(self) -> None:
        if self._vectorstore is None:
            return
        log.debug("Saving FAISS index to %s", self.index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self._vectorstore.save_local(str(self.index_path))

    def retriever(self, top_k: int) -> FAISS:
        store = self.load()
        if store is None:
            raise ValueError("RAG index is empty. Ingest documents before creating a retriever.")
        return store.as_retriever(search_kwargs={"k": max(1, top_k)})

    def similarity_search(
        self,
        query: str,
        top_k: int,
        *,
        metadata_filter: Optional[dict] = None,
    ) -> List[tuple[Document, float]]:
        store = self.load()
        if store is None:
            raise ValueError("RAG index is empty. Ingest documents before querying.")
        search_kwargs = {"k": max(1, top_k)}
        if metadata_filter:
            search_kwargs["filter"] = metadata_filter
        return store.similarity_search_with_score(query, **search_kwargs)

    def split_text(
        self,
        text: str,
        source: str | None = None,
        metadata: Optional[Dict[str, object]] = None,
    ) -> List[Document]:
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "。", "？", "！", "\n", "。"],
            keep_separator=True,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        base_meta: Dict[str, object] = {}
        if metadata:
            base_meta.update({k: v for k, v in metadata.items() if v is not None})
        if source and "source" not in base_meta:
            base_meta["source"] = source
        chunks = splitter.create_documents([text], metadatas=[base_meta])
        return chunks

    def ingest_documents(self, docs: Iterable[Document], save: bool = True) -> int:
        docs_list = list(docs)
        if not docs_list:
            return 0
        store = self.load()
        if store is None:
            log.info("Creating new FAISS index at %s", self.index_path)
            self.index_path.mkdir(parents=True, exist_ok=True)
            self._vectorstore = FAISS.from_documents(docs_list, self.embedding)
        else:
            store.add_documents(docs_list)
            self._vectorstore = store
        if save:
            self.save()
        return len(docs_list)

    def ingest_directory(self, path: Path, glob: str = "**/*") -> int:
        texts: List[Document] = []
        for file_path in path.glob(glob):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext in {".txt", ".md", ".markdown"}:
                text = file_path.read_text(encoding="utf-8")
            elif ext in {".json", ".jsonl"}:
                text = self._read_json(file_path)
            else:
                continue
            if ext in {".md", ".markdown"}:
                segments = preprocess_markdown_tables(text, str(file_path))
                for segment_text, meta in segments:
                    docs = self.split_text(segment_text, metadata=meta)
                    texts.extend(docs)
            else:
                docs = self.split_text(text, source=str(file_path))
                texts.extend(docs)
        if not texts:
            return 0
        log.info("Ingesting %d chunks into RAG store", len(texts))
        created = self.ingest_documents(texts)
        return created

    @staticmethod
    def _read_json(path: Path) -> str:
        data = path.read_text(encoding="utf-8")
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return data
        if isinstance(parsed, dict):
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        if isinstance(parsed, list):
            return "\n".join(json.dumps(item, ensure_ascii=False) for item in parsed)
        return data
