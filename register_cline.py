"""把 code-review-graph 注册进 Cline 的 cline_mcp_settings.json。

只做「增加/更新一个键」，**不动** 其它 MCP 条目；改之前先备份。

用法::

    <python> register_cline.py              # 注册（已存在则更新）
    <python> register_cline.py --unregister # 摘掉本条目
    <python> register_cline.py --dry-run    # 只看会写什么

默认目标文件：%USERPROFILE%\\.cline\\data\\settings\\cline_mcp_settings.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER_NAME = "code-review-graph"
DEFAULT_PYTHON = r"F:\conda\envs\MCP\python.exe"
DEFAULT_SETTINGS = Path.home() / ".cline" / "data" / "settings" / "cline_mcp_settings.json"


def build_entry(python_exe: str, launcher: Path, timeout: int) -> dict:
    """Cline 的条目格式：顶层 command/args（与工作区里 nx-mcp 的写法一致）。"""
    return {
        "command": python_exe,
        "args": [str(launcher)],
        "timeout": timeout,
        "env": {"PYTHONUTF8": "1"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="注册/注销 code-review-graph MCP")
    parser.add_argument("--settings", default=str(DEFAULT_SETTINGS), help="cline_mcp_settings.json 路径")
    parser.add_argument("--python", default=DEFAULT_PYTHON, help="跑 MCP 的 python.exe")
    parser.add_argument("--launcher", default=str(HERE / "crg_mcp.py"), help="启动脚本路径")
    parser.add_argument("--timeout", type=int, default=900, help="单次工具调用超时秒数")
    parser.add_argument("--unregister", action="store_true", help="删掉本条目")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    args = parser.parse_args()

    settings = Path(args.settings)
    if not settings.is_file():
        print(f"[register] 找不到设置文件：{settings}", file=sys.stderr)
        return 2

    data = json.loads(settings.read_text(encoding="utf-8-sig"))
    servers = data.setdefault("mcpServers", {})

    if args.unregister:
        if SERVER_NAME not in servers:
            print(f"[register] {SERVER_NAME} 本来就没注册，无需操作")
            return 0
        servers.pop(SERVER_NAME)
        action = "removed"
    else:
        python_exe = Path(args.python)
        launcher = Path(args.launcher)
        if not python_exe.is_file():
            print(f"[register] python 不存在：{python_exe}", file=sys.stderr)
            return 2
        if not launcher.is_file():
            print(f"[register] 启动脚本不存在：{launcher}", file=sys.stderr)
            return 2
        servers[SERVER_NAME] = build_entry(str(python_exe), launcher, args.timeout)
        action = "written"

    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    if args.dry_run:
        print(f"[register] dry-run ({action}) -> {settings}\n")
        print(payload)
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = settings.with_name(f"{settings.name}.crgbak-{stamp}")
    shutil.copy2(settings, backup)
    settings.write_text(payload, encoding="utf-8")

    print(f"[register] {action}: {SERVER_NAME} -> {settings}")
    print(f"[register] 备份: {backup}")
    print(f"[register] 当前 MCP: {', '.join(sorted(servers)) or '(空)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
