"""把 RAG 拆成「离线灌库」和「在线检索」两步，逐步打印，便于定位卡住的位置。

离线灌库 = 解析 PDF → 切块 → Embedding → 写入 .data/Chroma
在线检索 = 把查询句 Embedding → 向量相似度查找 → 返回文本块

这一步不启动 Agent，也不启动 FastAPI。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("CREWAI_STORAGE_DIR", str(PROJECT_ROOT / ".data"))
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")


def step_embedder() -> None:
    print("=" * 60)
    print("离线准备 A：确认官方 Embedding 客户端是否打到 DashScope")
    print("=" * 60)

    from crewai.rag.embeddings.factory import build_embedder

    api_base = os.getenv("EMBEDDING_API_BASE")
    model = os.getenv("EMBEDDING_MODEL")
    api_key = os.getenv("EMBEDDING_API_KEY")
    print(f"EMBEDDING_API_BASE = {api_base}")
    print(f"EMBEDDING_MODEL    = {model}")
    print("EMBEDDING_API_KEY  = 已加载（不打印）")

    embedder = build_embedder(
        {
            "provider": "openai",
            "config": {
                "api_key": api_key,
                "model_name": model,
                "api_base": api_base,
            },
        }
    )
    client = getattr(embedder, "client", None)
    base_url = getattr(client, "base_url", None)
    print(f"OpenAI 客户端实际 base_url = {base_url}")
    if client is not None:
        client.timeout = 20

    vectors = embedder(["头痛 体检"])
    print(f"官方 Embedding 函数调用成功，维度 = {len(vectors[0])}")
    print()


def step_parse_pdf() -> None:
    print("=" * 60)
    print("离线准备 B：只解析 PDF，不灌库")
    print("=" * 60)

    from crewai_tools.rag.data_types import DataType
    from crewai_tools.rag.source_content import SourceContent
    from rag.store import DEFAULT_PDF

    print(f"PDF 路径 = {DEFAULT_PDF}")
    loader = DataType.PDF_FILE.get_loader()
    result = loader.load(SourceContent(str(DEFAULT_PDF)))
    print(f"页数 = {result.metadata.get('num_pages')}")
    print(f"抽出字符数 = {len(result.content)}")
    print(f"正文开头：{result.content[:120]!r}")
    print()


def embed_text(text: str, timeout: int = 20) -> list[float]:
    import time

    import requests

    url = os.environ["EMBEDDING_API_BASE"].rstrip("/") + "/embeddings"
    headers = {
        "Authorization": f"Bearer {os.environ['EMBEDDING_API_KEY']}",
        "Content-Type": "application/json",
    }
    payload = {"model": os.environ["EMBEDDING_MODEL"], "input": text}
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            wait = attempt * 2
            print(f"  embedding 失败，{wait}s 后重试：{type(exc).__name__}")
            time.sleep(wait)
    raise RuntimeError(f"Embedding 连续失败：{last_error}") from last_error


def step_manual_chroma_ingest_and_search(query: str) -> None:
    """离线灌库 + 在线检索。Embedding 用已验证的 HTTP 接口，向量库用本地 Chroma。"""
    import time

    import chromadb
    from crewai_tools.rag.chunkers.text_chunker import TextChunker
    from crewai_tools.rag.data_types import DataType
    from crewai_tools.rag.source_content import SourceContent
    from rag.store import DEFAULT_PDF

    collection_name = "health_records"
    persist_dir = str(PROJECT_ROOT / ".data")

    print("=" * 60)
    print("离线灌库 C1：按较小块切开（官方默认 1500 对 DashScope 太容易超时）")
    print("=" * 60)
    loaded = DataType.PDF_FILE.get_loader().load(SourceContent(str(DEFAULT_PDF)))
    chunks = TextChunker(chunk_size=400, chunk_overlap=50).chunk(loaded.content)
    print(f"块数 = {len(chunks)}，长度 = {[len(chunk) for chunk in chunks]}")
    print()

    print("=" * 60)
    print("离线灌库 C2：逐条 embedding，写入本地 Chroma")
    print("=" * 60)
    chroma = chromadb.PersistentClient(path=persist_dir)
    collection = chroma.get_or_create_collection(name=collection_name)
    ids, documents, embeddings = [], [], []
    for index, chunk in enumerate(chunks):
        print(f"灌库 {index + 1}/{len(chunks)}，长度 {len(chunk)}")
        embeddings.append(embed_text(chunk))
        ids.append(f"health-{index}")
        documents.append(chunk)
        time.sleep(0.8)
    collection.upsert(ids=ids, documents=documents, embeddings=embeddings)
    print(f"灌库完成，collection 现有 {collection.count()} 条")
    print()

    print("=" * 60)
    print("在线检索 D：只把查询句向量化，再做相似度查找")
    print("=" * 60)
    print(f"查询 = {query}")
    query_embedding = embed_text(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=5)
    docs = results.get("documents") or [[]]
    distances = results.get("distances") or [[]]
    if not docs[0]:
        print("没有检索到内容")
        return
    for i, (doc, distance) in enumerate(zip(docs[0], distances[0]), 1):
        print(f"--- 结果 {i} distance={distance:.4f} ---")
        print(doc[:400])
        print()


def step_offline_ingest_and_online_search(query: str) -> None:
    print("=" * 60)
    print("对照：再创建一次官方 PDFSearchTool（构造时会再次灌库）")
    print("=" * 60)
    from tools.pdf_search import create_pdf_search_tool

    tool = create_pdf_search_tool()
    print("官方 Tool 已创建")
    print(tool.run(query=query))


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "张三九 头痛 体检"
    include_official_tool = "--with-official-tool" in sys.argv
    step_embedder()
    step_parse_pdf()
    step_manual_chroma_ingest_and_search(query)
    if include_official_tool:
        step_offline_ingest_and_online_search(query)
