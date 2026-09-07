"""FastAPI entry: ingest is a separate write path, chat only retrieves."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
load_dotenv(PROJECT_ROOT / ".env")
os.environ.setdefault("CREWAI_STORAGE_DIR", str(PROJECT_ROOT / ".data"))

from crewai import LLM  # noqa: E402
from crew import CrewtestprojectCrew  # noqa: E402
from rag.store import (  # noqa: E402
    DEFAULT_PDF,
    UPLOAD_DIR,
    get_knowledge_status,
    ingest_pdf,
    list_chunks,
)


PORT = int(os.getenv("PORT", "8012"))


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[Message]
    stream: bool = False


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    choices: list[ChatCompletionResponseChoice]


def build_llm() -> LLM:
    api_key = os.getenv("CHAT_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 CHAT_API_KEY，请复制 .env.example 为 .env 并填写配置。")

    kwargs: dict[str, Any] = {
        "model": os.getenv("CHAT_MODEL", "deepseek/deepseek-chat"),
        "api_key": api_key,
        "temperature": float(os.getenv("CHAT_TEMPERATURE", "0.2")),
        "timeout": float(os.getenv("CHAT_TIMEOUT_SECONDS", "90")),
        "max_retries": int(os.getenv("CHAT_MAX_RETRIES", "1")),
    }
    if base_url := os.getenv("CHAT_API_BASE"):
        kwargs["base_url"] = base_url
    return LLM(**kwargs)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the crew for online retrieval only. Ingest is never done here."""
    model = build_llm()
    app.state.crew_runner = CrewtestprojectCrew(model).crew()
    app.state.crew_lock = asyncio.Lock()
    app.state.ingest_lock = asyncio.Lock()
    yield


app = FastAPI(
    title="CrewAI RAG：灌库与问答分离",
    version="3.0.0",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    status = get_knowledge_status()
    ready = "可以问答" if status["ready_for_search"] else "知识库为空，请先灌库"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>CrewAI RAG 学习服务</title>
  <style>
    body {{ font-family: sans-serif; margin: 40px; max-width: 720px; line-height: 1.6; }}
    a {{ color: #0b57d0; }}
  </style>
</head>
<body>
  <h1>CrewAI RAG 学习服务</h1>
  <p>服务已启动。根路径以前没有页面，所以会 404；现在从这里进入。</p>
  <p>知识库：{status["collection"]}，{status["chunk_count"]} 块，{ready}</p>
  <ul>
    <li><a href="/knowledge">查看本地知识库文本块</a></li>
    <li><a href="/docs">Swagger 接口调试</a></li>
    <li><a href="/health">健康检查 JSON</a></li>
    <li><a href="/v1/knowledge">知识库 JSON</a></li>
  </ul>
  <p>完整问答请另开终端运行 <code>python apiTest.py</code>，不要关这个服务窗口。</p>
</body>
</html>"""


@app.get("/health")
async def health() -> dict[str, Any]:
    status = get_knowledge_status()
    status["status"] = "ok"
    return status


@app.get("/v1/knowledge/status")
async def knowledge_status() -> dict[str, Any]:
    return get_knowledge_status()


@app.get("/v1/knowledge")
async def knowledge_list(limit: int = 50) -> dict[str, Any]:
    status = get_knowledge_status()
    return {
        **status,
        "chunks": list_chunks(limit=limit),
    }


@app.get("/knowledge", response_class=HTMLResponse)
async def knowledge_workbench() -> str:
    """Simple local workbench for reading Chroma text chunks."""
    status = get_knowledge_status()
    rows = list_chunks(limit=100)
    items = []
    for row in rows:
        content = (
            row["content"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        source = (row.get("metadata") or {}).get("source", "")
        items.append(
            f"<article><h3>{row['id']}</h3><p class='meta'>source={source}</p>"
            f"<pre>{content}</pre></article>"
        )
    body = "".join(items) or "<p>知识库是空的。先运行 python ingest.py，或 POST /v1/documents 上传 PDF。</p>"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>本地知识库 Workbench</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; max-width: 960px; }}
    .meta {{ color: #555; }}
    pre {{ white-space: pre-wrap; background: #f6f6f6; padding: 12px; }}
  </style>
</head>
<body>
  <h1>本地 Chroma 知识库</h1>
  <p>目录：{status["chroma_dir"]}</p>
  <p>SQLite：{status["sqlite_file"]}</p>
  <p>collection：{status["collection"]}，块数：{status["chunk_count"]}</p>
  <p>这不是 MySQL，MySQL Workbench 打不开它。这里可以直接阅读文本块；向量本身是浮点数组，不适合当表格看。</p>
  {body}
</body>
</html>"""


@app.post("/v1/ingest")
async def ingest_default() -> dict[str, Any]:
    async with app.state.ingest_lock:
        try:
            return await asyncio.to_thread(ingest_pdf, DEFAULT_PDF)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/v1/documents")
async def upload_and_ingest(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="只接受 PDF 文件")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    target = UPLOAD_DIR / f"{uuid.uuid4().hex}-{safe_name}"
    content = await file.read()
    target.write_bytes(content)

    async with app.state.ingest_lock:
        try:
            return await asyncio.to_thread(ingest_pdf, target, safe_name)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


async def run_crew(topic: str) -> str:
    async with app.state.crew_lock:
        result = await asyncio.to_thread(
            app.state.crew_runner.kickoff,
            inputs={"topic": topic},
        )
    return str(result)


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if not request.messages:
        raise HTTPException(status_code=422, detail="messages 不能为空")

    status = get_knowledge_status()
    if not status["ready_for_search"]:
        raise HTTPException(
            status_code=409,
            detail="知识库为空。请先运行 python ingest.py，或 POST /v1/documents 上传 PDF。",
        )

    try:
        formatted_response = await run_crew(request.messages[-1].content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if request.stream:
        async def generate_stream():
            chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
            for line in formatted_response.splitlines(keepends=True):
                chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": line},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate_stream(), media_type="text/event-stream")

    return ChatCompletionResponse(
        choices=[
            ChatCompletionResponseChoice(
                index=0,
                message=Message(role="assistant", content=formatted_response),
            )
        ]
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=False)
