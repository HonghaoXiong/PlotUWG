#!/usr/bin/env python3
"""PlotUWG 打包入口（PyInstaller + pywebview 原生窗口）。

- 打开 App 直接显示原生 macOS 窗口（WKWebView 内嵌），不再调起浏览器
- 端口自动探测：8787 被占用时自动换 8788/8789…
- 所有输出写入 ~/Library/Application Support/H5TOUWG/app.log
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn
import webview

from app import app


class _Api:
    """原生对话框（pywebview JS bridge）。"""

    def choose_folder(self):
        try:
            res = webview.windows[0].create_file_dialog(
                webview.FileDialog.FOLDER_DIALOG)
            return res[0] if res else None
        except Exception:  # noqa: BLE001
            return None

    def choose_file(self):
        try:
            res = webview.windows[0].create_file_dialog(
                webview.FileDialog.OPEN_DIALOG,
                file_types=("HDF5/H5 文件 (*.h5;*.hdf5;*.hdf)", "所有文件 (*.*)"))
            return res[0] if res else None
        except Exception:  # noqa: BLE001
            return None

HOST = "127.0.0.1"
BASE_PORT = 8787
LOG_DIR = Path.home() / "Library" / "Application Support" / "PlotUWG"
WIN_W, WIN_H = 1500, 950


def _find_free_port(start: int = BASE_PORT, tries: int = 12) -> int:
    for p in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            try:
                if s.connect_ex((HOST, p)) != 0:
                    return p
            except OSError:
                return p
    return start + tries


def _wait_ready(host: str, port: int, timeout: float = 120.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{host}:{port}/api/health", timeout=1.5)
            return
        except Exception:  # noqa: BLE001
            time.sleep(0.8)


def _run_server(port: int) -> None:
    uvicorn.run(app, host=HOST, port=port, log_level="warning")


if __name__ == "__main__":
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _log = open(LOG_DIR / "app.log", "a", encoding="utf-8")
        sys.stdout = _log
        sys.stderr = _log
    except OSError:
        pass

    # matplotlib 字体缓存持久化（首次构建 10-30s，之后秒开）
    os.environ.setdefault("MPLCONFIGDIR", str(LOG_DIR / "mpl"))
    try:
        (LOG_DIR / "mpl").mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    def _warmup() -> None:
        """后台预热：窗口显示后并行加载 matplotlib（首次渲染不再等待）。"""
        try:
            import matplotlib  # noqa: F401
            import matplotlib.font_manager  # noqa: F401
            import matplotlib.pyplot  # noqa: F401
        except Exception:  # noqa: BLE001
            pass

    try:
        port = _find_free_port()
        print(f"PlotUWG native window -> http://{HOST}:{port}")
        threading.Thread(target=_run_server, args=(port,), daemon=True).start()
        threading.Thread(target=_warmup, daemon=True).start()
        _wait_ready(HOST, port)
        # 原生 macOS 窗口（WKWebView），关窗即退出
        webview.create_window(
            "PlotUWG",
            f"http://{HOST}:{port}",
            width=WIN_W,
            height=WIN_H,
            min_size=(1080, 680),
            background_color="#f5f5f7",
            js_api=_Api(),
        )
        webview.start()
    except Exception as e:  # noqa: BLE001
        try:
            print(f"FATAL: {e}", file=sys.stderr)
        except Exception:  # noqa: BLE001
            pass
        raise
