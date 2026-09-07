# CrewAI Engineer 学习仓库

用于记录我学习 CrewAI、多 Agent、Flow 和企业级 AI 工程的实践过程。

## 项目索引

| 项目 | 一句话说明 |
|---|---|
| [Course Generator](./course-generator-main/) | 输入课程主题，由多个 Agent 依次完成资料搜索、课程规划、内容编写、测验设计和代码审查。 |
| [Health Record RAG](./health-record-rag/) | 健康档案 PDF 先离线灌入本地 Chroma，再由两个 Agent 在线检索并生成 Markdown 报告。 |

## 仓库维护约定

- 今后的 CrewAI 学习项目都放在本仓库中，每个项目使用独立文件夹。
- 首页项目索引只用一句话区分项目，详细实现和学习记录写在各项目自己的 README 中。
- 文件夹使用清晰稳定的英文名称，不把虚拟环境、缓存、IDE 配置或密钥上传到 GitHub。

## Course Generator 学习记录

当前执行链路：

```text
Web Research
    → Curriculum Architect
    → Content Writer
    → Quiz Master
    → Code Reviewer
```

Flow 位于 Crew 外层，负责输入校验、状态保存、质量路由、重试和最终输出。

## 已完成的实践

- 理解 Agent、Task、Tool、Crew、Process 和 Flow 的职责边界。
- 在原课程生成流程最前面增加 Web Research Agent 和 Research Task。
- 使用 `SerperDevTool` 搜索资料，并使用 `ScrapeWebsiteTool` 读取网页。
- 将 Web Research 结果通过 Task Context 传给后续 Agent。
- 将模型切换为 DeepSeek，并通过环境变量读取 API Key。
- 统一要求 Agent 输出中文。
- 支持 Crew 直接运行和 Flow 编排运行。
- 学习一个 Task 为什么可能包含多次 LLM iteration 和 Tool 调用。
- 分析整条 Crew 重跑带来的重复搜索、Token 消耗和延迟问题。

## 当前待改进点

- Reviewer 仍使用关键词判断是否通过，下一步改为 Pydantic 结构化输出。
- 当前修改流程可能重跑完整 Crew，下一步根据问题类型实现局部重试。
- Web Research 结果尚未建立带 TTL 的缓存。
- 尚未加入每个 Agent、LLM 和 Tool 的调用次数与成本统计。
- 尚未使用 FastAPI 对外提供 HTTP API。

## 本地运行

```powershell
cd course-generator-main

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

$env:DEEPSEEK_API_KEY="your-deepseek-key"
$env:SERPER_API_KEY="your-serper-key"

python -m src.main "CrewAI Flow Tutorial" --flow
```

详细说明参见项目内的 [README](./course-generator-main/README.md)。

## 下一阶段学习路线

1. 使用 `ReviewResult` 和 `output_pydantic` 实现结构化审查结果。
2. 使用 Guardrail 检查 `status` 与 `issues` 是否逻辑一致。
3. 将各阶段结果保存在 Flow State，实现最小范围重试。
4. 为 Web Research 增加缓存键、TTL 和强制刷新机制。
5. 使用 FastAPI 提供课程生成接口，并补充任务状态查询。
6. 增加鉴权、限流、超时、日志、Trace 和成本预算。

## 安全说明

- `.env`、虚拟环境、缓存和 IDE 配置不会提交到仓库。
- API Key 只能通过环境变量配置，不能写入源码或 README。
- Web Research 获取的网页内容应视为不可信输入，Agent 应采用最小 Tool 权限。

---

## Health Record RAG 学习记录

当前执行链路：

```text
离线：PDF → 切块 → Embedding → 本地 Chroma
在线：用户问题 → 检索 Agent → 报告 Agent → output/health_report.md
```

已完成的实践：

- 把官方 `PDFSearchTool` 的「构造时灌库」拆成独立 ingest 与在线检索。
- 用 FastAPI 提供上传灌库、知识库查看和 OpenAI 兼容问答接口；没有 FastAPI 也能用命令行跑通。
- 处理 DashScope Embedding 对长文本超时：官方软切后再做 350 字硬上限。

详细说明参见 [health-record-rag/README.md](./health-record-rag/README.md)。

---

更新日期：2026-09-07
