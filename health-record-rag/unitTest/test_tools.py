"""单独测试写入工具和在线检索工具，不启动 Agent，也不灌库。

学习顺序：
1. 先测 FileWriterTool。
2. 先 python ingest.py 灌库，再测检索。检索不会解析 PDF。

用法（必须在项目根目录、已激活 venv）：
    python unitTest/test_tools.py --writer
    python ingest.py
    python unitTest/test_tools.py --search
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")
os.environ.setdefault("CREWAI_STORAGE_DIR", str(PROJECT_ROOT / ".data"))

from tools.pdf_search import create_pdf_search_tool
from tools.report_writer import create_report_writer_tool


def test_file_writer() -> None:
    print("=" * 60)
    print("1) 测试 FileWriterTool（不调用任何大模型）")
    print("=" * 60)

    tool = create_report_writer_tool()
    result = tool.run(
        filename="tool_smoke_test.md",
        directory="output",
        overwrite=True,
        content="# Tool 冒烟测试\n\n这一段不是 Agent 写的，是你直接调用官方 FileWriterTool 写进去的。\n",
    )
    output_file = PROJECT_ROOT / "output" / "tool_smoke_test.md"
    print(f"工具返回：{result}")
    print(f"文件是否存在：{output_file.is_file()}")
    if output_file.is_file():
        print("文件内容：")
        print(output_file.read_text(encoding="utf-8"))
    print("结论：写入链路通了。Agent 之后只是“决定什么时候调用这个工具”。")


def test_pdf_search(query: str) -> None:
    print("=" * 60)
    print("2) 测试在线检索（不会解析 PDF，也不会灌库）")
    print("=" * 60)
    from rag.store import get_knowledge_status

    status = get_knowledge_status()
    print(f"本地 Chroma：{status['chroma_dir']}")
    print(f"已入库块数：{status['chunk_count']}")
    if not status["ready_for_search"]:
        raise SystemExit("知识库为空。请先运行：python ingest.py")

    print(f"查询：{query}")
    tool = create_pdf_search_tool()
    result = tool.run(query=query)
    print("检索结果：")
    print(result)
    print()
    print("结论：问答侧只检索已有向量，不再上传或切 PDF。")


def main() -> None:
    parser = argparse.ArgumentParser(description="单独测试本项目的两个官方 Tool")
    parser.add_argument("--writer", action="store_true", help="只测 FileWriterTool")
    parser.add_argument("--search", action="store_true", help="只测 PDFSearchTool")
    parser.add_argument("--all", action="store_true", help="两个都测")
    parser.add_argument(
        "--query",
        default="张三九的头痛和体检记录",
        help="PDF 检索用的查询词",
    )
    args = parser.parse_args()

    if not (args.writer or args.search or args.all):
        parser.print_help()
        print("\n建议先运行：python unitTest/test_tools.py --writer")
        raise SystemExit(0)

    if args.writer or args.all:
        test_file_writer()
        print()

    if args.search or args.all:
        test_pdf_search(args.query)


if __name__ == "__main__":
    main()
