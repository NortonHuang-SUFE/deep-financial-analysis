# Daily Report Agent

[English](README.en.md)

面向中国二级市场的日报 Agent，用于生成 A 股开盘前日报，并按需渲染日报头图或视觉摘要。项目由一个公开 LangGraph graph 和两条内部能力组成：

- `morning_note`：生成 A 股开盘前 Morning Note / 日报 Markdown 与 JSON 来源 artifact。
- `html_image_renderer`：读取日报 artifact，渲染一张 HTML-based PNG 头图或视觉摘要。

公开 LangGraph graph 只有 `daily_report`。项目范围刻意收敛，不包含估值建模、个股覆盖、行业深度研究、股票筛选或 thesis tracker。

> 免责声明：本项目生成的是信息整理和投研工作底稿，不构成投资建议。所有结论都应由具备资质的专业人士复核。

## 产出

| 产出 | 说明 |
|---|---|
| `morning-note.md` | A 股盘前日报，覆盖隔夜市场、政策监管、公司事件、资金面和今日日程 |
| `morning-note-sources.json` | 日报结构化来源与核验信息 |
| `png/<seq>.png` | 可选日报头图 / 视觉摘要，由 `html_image_renderer` 从日报 artifact 渲染 |
| `daily-report-summary.md` | 顶层协调器写入的一次运行摘要和 artifact 索引 |

### 样例图

<p align="center">
  <img src="docs/assets/sample-leverage-flows-dashboard.png" alt="盘前两融资金主题 PC 头图" width="640"><br>
  <em>盘前两融资金主题 PC 头图：长电 · 恒逸 杠杆信号分化（2026-06-26）</em>
</p>

<p align="center">
  <img src="docs/assets/sample-storage-chain-poster.png" alt="市场主题电子杂志风海报" width="300"><br>
  <em>市场主题电子杂志风海报：存储链爆发 / 两融破 3 万亿（2026-06-24）</em>
</p>

## 配置

环境要求：

- Python 3.11
- OpenAI-compatible 模型网关，默认使用 DashScope / Volcengine 配置
- 同花顺 iFind MCP token 或完整 Authorization header
- 可选：东方财富妙想 MX DS MCP key

安装：

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e ./financial-agent-runtime \
  -e ./morning-note -e ./orchestrator -e ./html-image-renderer
```

配置：

```bash
cp .env.example .env
```

`.env` 中至少填写：

```bash
DASHSCOPE_API_KEY=...
ARK_API_KEY=...

# 二选一
IFIND_MCP_TOKEN=...
IFIND_MCP_AUTHORIZATION=Bearer ...
```

可以用本地配置页编辑模型 profile、`api_key_env` 变量名和 agent 绑定：

```bash
.venv/bin/python -m financial_agent_runtime.model_admin
```

打开 `http://127.0.0.1:8765`，保存后会更新根目录 `model-routing.yaml`。真实密钥只放在 `.env`。

## 运行

开发模式：

```bash
.venv/bin/langgraph dev --no-browser --no-reload
```

启动后选择 `daily_report`。常见请求：

```text
生成今天 A 股开盘前日报，并额外做一张 16:9 头图。
```

## 本地 / 内网 Docker

`langgraph.json` 是官方部署入口：`graphs` 决定公开 assistant，`dependencies` 决定容器安装的本地包。本项目只公开 `daily_report`。

生成 Dockerfile：

```bash
.venv/bin/langgraph dockerfile -c langgraph.json /private/tmp/daily-report.Dockerfile
```

生产形态本地验证：

```bash
.venv/bin/langgraph up --recreate --wait --port 8123
curl http://127.0.0.1:8123/ok
```

Docker 镜像会安装 Chromium 和中文字体，并设置 `HTML_IMAGE_RENDERER_BROWSER=/usr/bin/chromium`，用于 `html_image_renderer` 在容器内渲染 PNG。

## 运行模式

默认 `AGENT_BACKEND=local`，产物写入仓库或 `AGENT_FILE_STORAGE_ROOT` 指定目录。仍保留 Daytona backend 支持，但日报 Docker 部署建议优先使用 local backend 与容器文件系统。

## 测试

```bash
.venv/bin/python -m pytest financial-agent-runtime/tests morning-note/tests html-image-renderer/tests orchestrator/tests
```

## 版本

当前版本：`v0.1.1`。

完整版本历史见 [CHANGELOG.md](CHANGELOG.md)（English changelog: [CHANGELOG.en.md](CHANGELOG.en.md)）。
