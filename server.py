#!/usr/bin/env python3
"""H5Plot Studio 启动器：启动 FastAPI 并自动打开浏览器。

用法:
    python server.py [--port 8787] [--no-browser]

要求: geopixel 环境（h5py/numpy/scipy/matplotlib/ultraplot + fastapi/uvicorn）。
"""
from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    # 确保包路径可用（server.py 位于 h5plot_studio/ 下）
    HERE = Path(__file__).resolve().parent
    sys.path.insert(0, str(HERE))

    if not args.no_browser:
        webbrowser.open(f"http://{args.host}:{args.port}")

    import uvicorn
    uvicorn.run("app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()