"""Local Chroma store: ingest is offline, search is online.

Chroma lives on disk at ``.data/chroma.sqlite3``. There is no MySQL and no
separate Chroma server. Inspect chunks with ``list_chunks()`` or GET /v1/knowledge.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import chromadb
import requests
from chromadb.api.models.Collection import Collection
from crewai_tools.rag.chunkers.text_chunker import TextChunker
from crewai_tools.rag.data_types import DataType
from crewai_tools.rag.source_content import SourceContent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = PROJECT_ROOT / ".data"
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
DEFAULT_PDF = (
    PROJECT_ROOT / "unitTest" / "vectorSaveTest" / "input" / "健康档案.pdf"
)
COLLECTION_NAME = "health_records"

CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
# 官方 TextChunker 的 chunk_size 是软目标，中文 PDF 经常切出 700~1400 字。
# DashScope 对约 800 字请求会挂死，这里再做一次硬上限。
MAX_EMBED_CHARS = 350
EMBED_TIMEOUT_SECONDS = 30
EMBED_SLEEP_SECONDS = 1.2


def enforce_max_chunk_length(chunks: list[str], max_chars: int = MAX_EMBED_CHARS) -> list[str]:
    """Hard-split any chunk that is longer than max_chars.

    Prefer breaking on newlines so sentences stay readable. This is the actual
    size sent to the embedding API; the official TextChunker size is only a hint.
    """
    result: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            result.append(chunk)
            continue
        start = 0
        while start < len(chunk):
            end = min(start + max_chars, len(chunk))
            piece = chunk[start:end]
            if end < len(chunk):
                newline_at = piece.rfind("\n")
                if newline_at >= max_chars // 3:
                    piece = piece[: newline_at + 1]
                    end = start + newline_at + 1
            text = piece.strip()
            if text:
                result.append(text)
            start = end
    return result


def _require_embedding_config() -> tuple[str, str, str]:
    api_key = os.getenv("EMBEDDING_API_KEY")
    api_base = os.getenv("EMBEDDING_API_BASE", "").rstrip("/")
    model = os.getenv("EMBEDDING_MODEL")
    if not api_key:
        raise RuntimeError("缺少 EMBEDDING_API_KEY")
    if not api_base:
        raise RuntimeError("缺少 EMBEDDING_API_BASE")
    if not model:
        raise RuntimeError("缺少 EMBEDDING_MODEL")
    return api_key, api_base, model


def embed_text(text: str) -> list[float]:
    """Call the OpenAI-compatible embedding HTTP API for one text."""
    api_key, api_base, model = _require_embedding_config()
    url = f"{api_base}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "input": text}
    last_error: Exception | None = None
    for attempt in range(1, 5):
        started = time.time()
        print(
            f"    正在请求 Embedding（第 {attempt} 次）{api_base}  model={model}  "
            f"最长等待 {EMBED_TIMEOUT_SECONDS}s ...",
            flush=True,
        )
        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=EMBED_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            vector = response.json()["data"][0]["embedding"]
            print(
                f"    Embedding 成功，{time.time() - started:.2f}s，"
                f"{len(text)} 字，向量维度 {len(vector)}",
                flush=True,
            )
            return vector
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            wait = attempt * 3
            print(
                f"    Embedding 超时/失败（第 {attempt} 次，已等 {time.time() - started:.1f}s）："
                f"{type(exc).__name__}，{wait}s 后重试",
                flush=True,
            )
            time.sleep(wait)
    raise RuntimeError(f"Embedding 连续失败：{last_error}") from last_error


def get_collection() -> Collection:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME)


def get_knowledge_status() -> dict[str, Any]:
    collection = get_collection()
    sqlite_path = CHROMA_DIR / "chroma.sqlite3"
    return {
        "collection": COLLECTION_NAME,
        "chunk_count": collection.count(),
        "chroma_dir": str(CHROMA_DIR),
        "sqlite_file": str(sqlite_path),
        "sqlite_exists": sqlite_path.is_file(),
        "ready_for_search": collection.count() > 0,
    }


def list_chunks(limit: int = 50) -> list[dict[str, Any]]:
    """Return stored text chunks. This does not call Embedding."""
    collection = get_collection()
    raw = collection.get(include=["documents", "metadatas"], limit=limit)
    ids = raw.get("ids") or []
    documents = raw.get("documents") or []
    metadatas = raw.get("metadatas") or []
    rows: list[dict[str, Any]] = []
    for index, doc_id in enumerate(ids):
        rows.append(
            {
                "id": doc_id,
                "content": documents[index] if index < len(documents) else "",
                "metadata": metadatas[index] if index < len(metadatas) else {},
            }
        )
    return rows


def search_chunks(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Online retrieval only: embed the query, then search existing vectors."""
    collection = get_collection()
    if collection.count() == 0:
        raise RuntimeError("知识库为空，请先上传文档并灌库。")
    query_embedding = embed_text(query)
    raw = collection.query(query_embeddings=[query_embedding], n_results=limit)
    documents = (raw.get("documents") or [[]])[0]
    distances = (raw.get("distances") or [[]])[0]
    ids = (raw.get("ids") or [[]])[0]
    metadatas = (raw.get("metadatas") or [[]])[0]
    hits: list[dict[str, Any]] = []
    for index, content in enumerate(documents):
        hits.append(
            {
                "id": ids[index] if index < len(ids) else "",
                "content": content,
                "distance": distances[index] if index < len(distances) else None,
                "metadata": metadatas[index] if index < len(metadatas) else {},
            }
        )
    return hits


def ingest_pdf(pdf_path: str | Path, source_name: str | None = None) -> dict[str, Any]:
    """Offline ingest: parse → chunk → embed → upsert. Never used by Q&A."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"找不到 PDF：{path}")

    print(f"[1/5] 读取 PDF：{path}", flush=True)
    started = time.time()
    loaded = DataType.PDF_FILE.get_loader().load(SourceContent(str(path.resolve())))
    print(
        f"[1/5] 读取完成，{time.time() - started:.2f}s，"
        f"{loaded.metadata.get('num_pages')} 页，{len(loaded.content)} 字",
        flush=True,
    )

    print(
        f"[2/5] 先用官方 TextChunker 软切（目标 {CHUNK_SIZE}，overlap {CHUNK_OVERLAP}）",
        flush=True,
    )
    soft_chunks = TextChunker(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    ).chunk(loaded.content)
    print(f"[2/5] 软切结果 {len(soft_chunks)} 块，长度={ [len(c) for c in soft_chunks] }", flush=True)
    chunks = enforce_max_chunk_length(soft_chunks, MAX_EMBED_CHARS)
    if not chunks:
        raise ValueError(f"PDF 没有抽出可灌库文本：{path}")
    oversize = [len(c) for c in chunks if len(c) > MAX_EMBED_CHARS]
    print(
        f"[2/5] 硬上限 {MAX_EMBED_CHARS} 字后再切，得到 {len(chunks)} 块，"
        f"长度={ [len(c) for c in chunks] }",
        flush=True,
    )
    if oversize:
        raise RuntimeError(f"仍有超长块：{oversize}")

    print(f"[3/5] 打开本地 Chroma：{CHROMA_DIR}", flush=True)
    collection = get_collection()
    print(
        f"[3/5] collection={COLLECTION_NAME}，当前已有 {collection.count()} 块",
        flush=True,
    )

    source = source_name or path.name
    ids: list[str] = []
    documents: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict[str, Any]] = []

    print("[4/5] 开始逐块 Embedding（慢通常发生在这一步）", flush=True)
    for index, chunk in enumerate(chunks):
        preview = chunk.replace("\n", " ")[:40]
        print(
            f"[4/5] 第 {index + 1}/{len(chunks)} 块，{len(chunk)} 字，预览：{preview}",
            flush=True,
        )
        embeddings.append(embed_text(chunk))
        ids.append(f"{path.stem}-{index}")
        documents.append(chunk)
        metadatas.append(
            {
                "source": source,
                "chunk_index": index,
                "total_chunks": len(chunks),
                "file_name": path.name,
            }
        )
        if index < len(chunks) - 1:
            print(f"    间隔 {EMBED_SLEEP_SECONDS}s，降低限流概率", flush=True)
            time.sleep(EMBED_SLEEP_SECONDS)

    print(f"[5/5] 写入本地 Chroma，共 {len(ids)} 块", flush=True)
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    print(f"[5/5] 写入完成，库中现有 {collection.count()} 块", flush=True)
    return {
        "source": source,
        "pdf_path": str(path.resolve()),
        "pages": loaded.metadata.get("num_pages"),
        "ingested_chunks": len(chunks),
        "collection": COLLECTION_NAME,
        "chunk_count": collection.count(),
        "chroma_dir": str(CHROMA_DIR),
    }
