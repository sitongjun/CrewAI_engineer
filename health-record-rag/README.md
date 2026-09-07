# Health Record RAG

CrewAI 健康档案 RAG 学习项目：离线灌库与在线问答分开。输入一份 PDF 健康档案，先写入本地 Chroma，再由两个 Agent 检索并生成中文 Markdown 报告。

这是 [CrewAI_engineer](https://github.com/sitongjun/CrewAI_engineer) 里的第二个学习项目，用来练习企业里常见的「文档上传即灌库、问答服务只检索」。

## 为什么不用官方 RagTool / PDFSearchTool

官方 `PDFSearchTool` 继承 `RagTool`，**只做检索，本来就不会生成报告**。写 Markdown 一直是另一条线：`report_agent` + 官方 `FileWriterTool`。

官方检索工具和现在的在线检索，目标一样：把问题变成向量，从知识库里找出相近文本。差别在职责有没有拆开：

| | 官方 `PDFSearchTool(pdf=...)` | 本项目 |
|---|---|---|
| 解析 PDF、切块、Embedding、写入 Chroma | 创建工具时就会做（离线 + 在线绑在一起） | `python ingest.py` 或 `POST /v1/documents` |
| 用户提问时 | 可能再次灌库 | 只检索已有向量 |
| 生成 `health_report.md` | 不做 | `report_agent` + `FileWriterTool` |

本机实测：官方工具构造时会把多个长块一次送给 DashScope Embedding，请求挂死超时。所以问答侧改成自写的 `KnowledgeSearchTool`，内部调用 `rag.store.search_chunks()`。检索语义没变，只是不再在启动时灌库。

## 架构

```text
离线灌库（不启动 FastAPI 也能做）
  健康档案.pdf
  -> 解析 + 切块（软切后再硬限制 350 字）
  -> DashScope Embedding
  -> 本地 .data/chroma.sqlite3

在线问答
  用户问题
  -> retrieval_agent 调用 Search ingested health records
  -> 只查 Chroma
  -> report_agent 调用 FileWriterTool
  -> output/health_report.md
```

FastAPI 是可选外壳。没有它也可以：

```powershell
python ingest.py
python unitTest/test_tools.py --search
```

完整 Crew 也可以直接 `crew.kickoff(...)`。`python main.py` 只是把这些能力变成 HTTP，方便浏览器和 `apiTest.py`。

## 每个文件做什么

### 离线灌库

| 文件 | 作用 |
|---|---|
| `ingest.py` | 命令行入口：灌库或 `--inspect` 查看文本块 |
| `rag/store.py` | 核心：解析 PDF、切块、Embedding、写入/查询 Chroma |
| `rag/__init__.py` | 导出 store 里的函数 |
| `unitTest/vectorSaveTest/input/健康档案.pdf` | 示例知识库原文（虚构人物张三九） |
| `data/uploads/` | `POST /v1/documents` 上传的 PDF 落盘位置 |

### 在线检索与问答

| 文件 | 作用 |
|---|---|
| `tools/pdf_search.py` | 在线检索 Tool，不解析 PDF、不灌库 |
| `tools/report_writer.py` | 配置官方 `FileWriterTool`，写出 Markdown |
| `tools/__init__.py` | 导出两个 Tool 工厂 |
| `config/agents.yaml` | 检索专家、报告专家的人设 |
| `config/tasks.yaml` | 两个 Task 的说明书 |
| `crew.py` | 两个 Agent 顺序执行的 Crew |

### HTTP 外壳（可选）

| 文件 | 作用 |
|---|---|
| `main.py` | FastAPI：首页、知识库页、上传灌库、OpenAI 兼容问答接口 |
| `apiTest.py` | 调用 `/v1/chat/completions` 的小客户端 |

### 学习用测试

| 文件 | 作用 |
|---|---|
| `unitTest/test_embedding_api.py` | 只测 Embedding HTTP，确认 Key/模型/网络 |
| `unitTest/test_tools.py` | `--writer` 测写文件；`--search` 测在线检索 |
| `unitTest/test_offline_and_search.py` | 逐步拆开灌库和检索，方便定位卡在哪一步 |

### 配置与输出

| 文件 | 作用 |
|---|---|
| `.env.example` | 环境变量模板。聊天模型和 Embedding 是两套 Key |
| `.env` | 本地真实 Key，**不要提交 GitHub** |
| `requirements.txt` | Python 依赖 |
| `.gitignore` | 忽略 venv、`.env`、`.data`、`output` |
| `output/health_report.md` | 问答生成的报告，本地产生，不入库 |

不需要阅读：`venv/`、`venv_py310_ssl_broken/`、`.data/`、`.idea/`。

## 本地 Chroma 在哪

在本机磁盘，不需要 MySQL，也不需要单独启动 Chroma。

| 想看什么 | 怎么看 |
|---|---|
| 文件 | `.data/chroma.sqlite3` |
| 文本块 | `python ingest.py --inspect` 或 http://127.0.0.1:8012/knowledge |
| JSON | http://127.0.0.1:8012/v1/knowledge |
| MySQL Workbench | 打不开。这是 SQLite 向量库 |

## 怎么跑

在项目目录激活虚拟环境后：

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，填写 `CHAT_API_KEY` 和 `EMBEDDING_API_KEY`。

```powershell
python ingest.py
python ingest.py --inspect
python unitTest/test_tools.py --search --query "张三九的头痛和体检记录"
python main.py
```

另开终端：

```powershell
python apiTest.py
```

报告在 `output/health_report.md`。

## 接口

服务启动后：

- 首页：http://127.0.0.1:8012/
- 知识库：http://127.0.0.1:8012/knowledge
- Swagger：http://127.0.0.1:8012/docs
- 上传即灌库：`POST /v1/documents`
- 问答：`POST /v1/chat/completions`

## 重要说明

只用于学习。健康报告不能替代医生诊断；真实健康档案不要发给未评估的第三方模型。不要把 `.env` 提交到 GitHub。
