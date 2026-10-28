"""code-review-graph MCP 自检：用真实 MCP 客户端走一遍 stdio 握手。

验证的是「Cline 会看到什么」——不是 import，而是 ``initialize`` + ``tools/list``
能否正常往返。任何 stdout 污染、编码错误、启动脚本语法问题都会在这里暴露。

用法::

    F:\\conda\\envs\\MCP\\python.exe E:\\cline\\mcp\\code_review_graph\\selftest.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: 探测用的仓库根。这里只要是个存在的目录即可 —— serve 阶段不建图。
PROBE_REPO = os.environ.get("CRG_SELFTEST_REPO") or str(HERE)


async def _run() -> int:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(HERE / "crg_mcp.py"), "--repo", PROBE_REPO],
        env=env,
        cwd=str(HERE),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            info = getattr(init, "serverInfo", None)
            print(f"[selftest] 握手成功: {getattr(info, 'name', '?')} "
                  f"{getattr(info, 'version', '?')}")

            listed = await session.list_tools()
            names = sorted(t.name for t in listed.tools)
            print(f"[selftest] 工具数: {len(names)}")
            for name in names:
                print(f"  - {name}")

            prompts = await session.list_prompts()
            if prompts.prompts:
                print(f"[selftest] prompt 数: {len(prompts.prompts)}"
                      f" -> {', '.join(p.name for p in prompts.prompts)}")

    return 0 if names else 1


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
