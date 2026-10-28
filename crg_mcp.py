"""code-review-graph MCP 启动器（Cline 用）。

职责只有三件事，其余全部交给上游的 ``code_review_graph.main.main()``：

1. 把 ``CRG_HOME``（注册表 / 守护进程 PID / watch 配置 / 日志的根）固定到本目录
   下的 ``data\\``，这样这套 MCP 的数据不会散落在 ``C:\\Users\\<用户>\\.code-review-graph``；
2. 从同目录的 ``config.json`` 读取默认仓库、自动 watch、工具白名单；
3. 调 ``main(repo_root=..., tools=..., auto_watch=...)`` 起 stdio MCP 服务。

用法（Cline 的 cline_mcp_settings.json 里就是这样配的）::

    F:\\conda\\envs\\MCP\\python.exe  E:\\cline\\mcp\\code_review_graph\\crg_mcp.py

手工排障::

    <python> crg_mcp.py --check        # 只打印环境，不启动服务（输出到 stderr）
    <python> crg_mcp.py --repo D:\\code\\myproj --auto-watch

注意：stdio MCP 要求 **stdout 只能有 JSON-RPC**，因此本文件的任何提示都写 stderr。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"


def _force_utf8_stderr() -> None:
    """把 stderr 钉成 UTF-8。

    Windows 默认 stderr 是 GBK（cp936）：一旦上游库把含中文的路径/错误打到
    stderr，Python 会抛 ``UnicodeEncodeError`` 直接把服务进程弄崩。stdio MCP
    的 stdout 必须是纯 JSON-RPC，不能碰；stderr 可以安全地重配。
    """
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):  # 非 TextIOWrapper（被重定向成管道对象等）
        pass


def _stderr(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def load_config() -> dict:
    """读取 config.json；不存在或损坏时返回空配置（服务照常能起）。"""
    if not CONFIG_PATH.is_file():
        return {}
    try:
        with CONFIG_PATH.open("r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        _stderr(f"[crg_mcp] config.json 读取失败，已忽略：{exc}")
        return {}
    return data if isinstance(data, dict) else {}


def resolve_crg_home(cfg: dict) -> Path:
    """确定 CRG_HOME 的落点。

    优先级：进程里已有的 CRG_HOME > config.json 的 ``crg_home``（相对本目录）
    > 本目录下的 ``data``。
    """
    existing = os.environ.get("CRG_HOME", "").strip()
    if existing:
        return Path(existing).expanduser()

    configured = str(cfg.get("crg_home") or "data").strip() or "data"
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = HERE / path
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crg_mcp.py",
        description="code-review-graph 的 MCP 启动器（默认 stdio 传输）",
    )
    parser.add_argument("--repo", default=None, help="默认仓库根目录；留空则用 Cline 的工作区目录")
    parser.add_argument("--auto-watch", action="store_true", help="后台线程监听文件变化，自动增量更新")
    parser.add_argument("--tools", default=None, help="工具白名单（逗号分隔），留空=全部")
    parser.add_argument("--check", action="store_true", help="只打印环境信息后退出，不启动服务")
    return parser


def main() -> int:
    _force_utf8_stderr()
    args = build_parser().parse_known_args()[0]
    cfg = load_config()

    crg_home = resolve_crg_home(cfg)
    crg_home.mkdir(parents=True, exist_ok=True)
    os.environ["CRG_HOME"] = str(crg_home)
    (HERE / "logs").mkdir(exist_ok=True)

    repo = args.repo or str(cfg.get("default_repo") or "").strip() or None
    tools = args.tools or str(cfg.get("tools") or "").strip() or None
    auto_watch = args.auto_watch or bool(cfg.get("auto_watch", False))

    if args.check:
        import code_review_graph

        _stderr("[crg_mcp] ---- environment ----")
        _stderr(f"[crg_mcp] python     : {sys.executable}")
        _stderr(f"[crg_mcp] version    : {sys.version.split()[0]}")
        _stderr(f"[crg_mcp] package    : {Path(code_review_graph.__file__).parent}")
        _stderr(f"[crg_mcp] pkg version: {getattr(code_review_graph, '__version__', 'n/a')}")
        _stderr(f"[crg_mcp] CRG_HOME   : {crg_home}")
        _stderr(f"[crg_mcp] config     : {CONFIG_PATH} (exists={CONFIG_PATH.is_file()})")
        _stderr(f"[crg_mcp] repo       : {repo or '(cwd) ' + os.getcwd()}")
        _stderr(f"[crg_mcp] auto_watch : {auto_watch}")
        _stderr(f"[crg_mcp] tools      : {tools or '(all)'}")
        return 0

    try:
        from code_review_graph.main import main as serve_main
    except ImportError as exc:  # 依赖没装好时给出可执行的提示
        _stderr(
            "[crg_mcp] cannot import code_review_graph. Install it first:\n"
            f"    {sys.executable} -m pip install code-review-graph==2.3.9\n"
            f"original error: {exc}"
        )
        return 1

    serve_main(repo_root=repo, tools=tools, auto_watch=auto_watch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
