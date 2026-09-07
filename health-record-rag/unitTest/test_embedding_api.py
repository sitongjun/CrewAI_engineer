"""只测 Embedding HTTP 接口，不创建 PDFSearchTool，也不启动 Agent。

这一步用来确认：Key、模型名、Base URL、网络是否通。
通过之后，再测 PDFSearchTool 才有意义。
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def main() -> None:
    api_key = os.getenv("EMBEDDING_API_KEY")
    api_base = os.getenv("EMBEDDING_API_BASE", "").rstrip("/")
    model = os.getenv("EMBEDDING_MODEL")

    if not api_key:
        raise SystemExit("缺少 EMBEDDING_API_KEY")
    if not api_base:
        raise SystemExit("缺少 EMBEDDING_API_BASE")
    if not model:
        raise SystemExit("缺少 EMBEDDING_MODEL")

    url = f"{api_base}/embeddings"
    print(f"请求地址：{url}")
    print(f"模型：{model}")
    print("Key 已加载，但不会打印。超时 20 秒。")

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "input": "头痛 体检"},
        timeout=20,
    )
    print(f"HTTP 状态码：{response.status_code}")

    data = response.json()
    if response.ok:
        vector = data["data"][0]["embedding"]
        print(f"成功：向量维度 = {len(vector)}")
        print("结论：Embedding 接口通了，接下来才能测 PDFSearchTool。")
        return

    error = data.get("error") or data.get("message") or data
    print(f"失败：{error}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
