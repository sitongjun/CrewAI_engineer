"""Offline document ingest. Q&A never runs this module.

用法（项目根目录、已激活 venv）：
    python ingest.py
    python ingest.py --pdf "unitTest/vectorSaveTest/input/健康档案.pdf"
    python ingest.py --inspect
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# PowerShell 默认会缓冲 stdout，不 flush 就会看起来像卡住。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)


PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
load_dotenv(PROJECT_ROOT / ".env")
os.environ.setdefault("CREWAI_STORAGE_DIR", str(PROJECT_ROOT / ".data"))

from rag.store import DEFAULT_PDF, get_knowledge_status, ingest_pdf, list_chunks


def print_status() -> None:
    status = get_knowledge_status()
    print("本地 Chroma 位置：", status["chroma_dir"], flush=True)
    print("SQLite 文件：    ", status["sqlite_file"], flush=True)
    print("collection：     ", status["collection"], flush=True)
    print("已入库块数：     ", status["chunk_count"], flush=True)
    print(
        "可否在线检索：   ",
        "可以" if status["ready_for_search"] else "还不能，请先灌库",
        flush=True,
    )


def print_chunks(limit: int) -> None:
    rows = list_chunks(limit=limit)
    if not rows:
        print("知识库是空的。先运行：python ingest.py")
        return
    for row in rows:
        print("=" * 60)
        print(f"id={row['id']}  metadata={row['metadata']}")
        print(row["content"][:500])
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="离线灌库 / 查看本地 Chroma")
    parser.add_argument("--pdf", default=str(DEFAULT_PDF), help="要灌库的 PDF 路径")
    parser.add_argument("--inspect", action="store_true", help="只查看，不灌库，不调用 Embedding")
    parser.add_argument("--limit", type=int, default=50, help="查看时最多显示多少块")
    args = parser.parse_args()

    if args.inspect:
        print_status()
        print()
        print_chunks(args.limit)
        return

    print("=" * 60, flush=True)
    print("离线灌库开始", flush=True)
    print(f"PDF：{args.pdf}", flush=True)
    print("=" * 60, flush=True)
    result = ingest_pdf(args.pdf)
    print("=" * 60, flush=True)
    print("灌库完成", flush=True)
    for key, value in result.items():
        print(f"  {key}: {value}", flush=True)
    print(flush=True)
    print_status()
    print(flush=True)
    print("查看全部文本块：python ingest.py --inspect", flush=True)
    print("或打开 http://127.0.0.1:8012/knowledge 与 Swagger /v1/knowledge", flush=True)


if __name__ == "__main__":
    main()
