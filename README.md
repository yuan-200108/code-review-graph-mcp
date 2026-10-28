# code-review-graph MCP（Cline 用）

`code-review-graph` 是一个**本地代码知识图谱**：用 Tree-sitter 把代码解析成
「函数 / 类 / 导入」节点和「调用 / 继承 / 导入 / 测试」边，存进 SQLite，
再通过 MCP 把**按需切片**的结果喂给 AI。目的是做代码审查时不用把整个仓库塞进上下文。

- 上游项目：https://github.com/tirth8205/code-review-graph
- 版本：2.3.9（PyPI）
- 注册名：`code-review-graph`
- 传输：stdio

## 目录里有什么

```
E:\cline\mcp\code_review_graph\
├── crg_mcp.py          # 启动器（Cline 直接跑这个）
├── register_cline.py   # 注册/注销 Cline 配置项（会先备份）
├── selftest.py         # 自检：真实 MCP 客户端握手 + tools/list
├── config.json         # 本目录的配置（默认仓库 / auto_watch / 工具白名单）
├── data\               # CRG_HOME：注册表、守护进程状态、watch 配置、日志
├── logs\               # 排障输出（可随时清空）
├── pip-freeze.before.txt  # 装依赖前的环境快照，回滚用
└── README.md
```

依赖装在现有 conda 环境 `F:\conda\envs\MCP`（与 nx-mcp / ppt-mcp / caxa-mcp / pet-mcp 共用），
本目录只放启动器和配置。

## Cline 里的配置项

`C:\Users\YWJ\.cline\data\settings\cline_mcp_settings.json`：

```json
"code-review-graph": {
  "command": "F:\\conda\\envs\\MCP\\python.exe",
  "args": ["E:\\cline\\mcp\\code_review_graph\\crg_mcp.py"],
  "timeout": 900,
  "env": { "PYTHONUTF8": "1" }
}
```

改完配置需要重载 Cline（命令面板 → `Developer: Reload Window`）。

## 怎么用

**第一次用某个项目，必须先建图**，否则图查询全是空的：

```
给这个项目建 code review 图                              → build_or_update_graph_tool
```

之后常用的：

| 想干什么 | 工具 |
|---|---|
| 看我这次改了什么、风险多大 | `detect_changes_tool` |
| 改这个函数会炸到谁 | `get_impact_radius_tool` |
| 谁调用了 `foo()` / `foo()` 调了谁 | `query_graph_tool` (callers_of / callees_of / imports_of / tests_for) |
| 按名字/关键词找函数类 | `semantic_search_nodes_tool` |
| 只给我相关几段源码（省 token） | `get_review_context_tool` / `get_minimal_context_tool` |
| 整体架构 / 模块聚类 | `get_architecture_overview_tool`、`list_communities_tool` |
| 找死代码、规划改名 | `refactor_tool`、`apply_refactor_tool` |
| 多仓库 | `list_repos_tool`、`cross_repo_search_tool` |

共 30 个工具 + 5 个 prompt（`review_changes`、`architecture_map`、`debug_issue`、
`onboard_developer`、`pre_merge_check`）。

**审查非当前工作区的项目**：不用改配置，在工具调用里传 `repo_root` 即可
（优先级：调用参数 > `--repo` > Cline 工作区目录）。

## 数据落在哪

| 内容 | 位置 |
|---|---|
| 本 MCP 的状态（注册表 / 守护进程 / watch 配置） | `E:\cline\mcp\code_review_graph\data\` |
| 每个仓库的图数据库 | `<被审查仓库>\.code-review-graph\graph.db` |

graph.db 在被审查仓库内部，所以 `.code-review-graph/` 会出现在你的项目里
（工具会自动往里写 `.gitignore`）。想放到别处就用 CLI 的 `--data-dir`。

## 排障

```powershell
# 1. 环境对吗（不启动服务，输出到 stderr）
F:\conda\envs\MCP\python.exe E:\cline\mcp\code_review_graph\crg_mcp.py --check

# 2. 握手 + 列工具（应输出 工具数: 30）
F:\conda\envs\MCP\python.exe E:\cline\mcp\code_review_graph\selftest.py

# 3. 重启注册项（会备份成 .crgbak-<时间戳>）
F:\conda\envs\MCP\python.exe E:\cline\mcp\code_review_graph\register_cline.py
```

注意：PowerShell 会把本程序的 stderr 当错误显示（`Command exited with code 1`），
只要 stderr 里是 `[crg_mcp] ...` / `INFO Starting MCP server` 就是正常的。
要看干净输出请用 `Start-Process -RedirectStandardOutput/-RedirectStandardError`。

## 升级

```powershell
F:\conda\envs\MCP\python.exe -m pip install --upgrade code-review-graph
```

上游会自己跑数据库迁移（日志里能看到 `Running migration v13` 之类）。

## 卸载

```powershell
F:\conda\envs\MCP\python.exe E:\cline\mcp\code_review_graph\register_cline.py --unregister
F:\conda\envs\MCP\python.exe -m pip uninstall -y code-review-graph tree-sitter tree-sitter-language-pack tree-sitter-c-sharp tree-sitter-yaml tree-sitter-embedded-template
Remove-Item -LiteralPath 'E:\cline\mcp\code_review_graph' -Recurse -Force
```

被审查仓库里的 `.code-review-graph\` 需要自己删（每个项目一份）。

## 已知取舍

- **独立 venv 没做**：依赖与另外 4 个 MCP 共用 `F:\conda\envs\MCP`，
  以后升级那个环境时留意 `fastmcp` / `mcp` 版本（本 MCP 要求 `fastmcp>=3.2.4,<4`、`mcp>=1,<3`）。
- **语义搜索降级**：没装 `sentence-transformers` 时 `semantic_search_nodes_tool` 走 FTS 全文检索
  （`search_mode: "fts"`），不是向量检索。要向量检索装 `pip install "code-review-graph[embeddings]"`
  并用 `embed_graph_tool` 建索引。
- **auto_watch 默认关**：开（`config.json` 里 `"auto_watch": true`）会起后台线程监听文件变化，
  大仓库吃 CPU，按需开。
- Python 3.14 上 tree-sitter 用的是预编译 wheel，已实测可用；换 Python 版本需重新验证。
