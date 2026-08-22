"""H5Plot Studio — FastAPI 后端入口。

本地 localhost 服务。只读 h5/目录；写操作仅限用户指定的导出目录与
userdata/（渲染中间产物/配置记忆），不触碰模型输出。
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import config as C
from core import h5inspector

# 注意：plotters/probe 涉及 matplotlib，延迟到路由内 import（启动提速，不阻塞窗口）

app = FastAPI(title="H5Plot Studio", version="0.4.2")

# PyInstaller 打包后 web/ 位于 _MEIPASS；源码运行时位于本文件旁
if getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
else:
    BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def index():
    # HTML 入口不缓存（静态资源带版本号查询串，可长缓存）
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/health")
def health():
    return {"ok": True}


# --------------------------------------------------------------------------
# 目录与文件
# --------------------------------------------------------------------------
class OpenReq(BaseModel):
    path: str
    kind: str = "dir"          # dir | file


@app.post("/api/dirs")
def list_dir(req: OpenReq):
    if req.kind != "dir":
        raise HTTPException(400, "kind 必须为 dir")
    out = h5inspector.directory_listing(req.path)
    if out.get("error"):
        raise HTTPException(400, out["error"])
    C.save_recent_path(out["path"])
    return out


@app.post("/api/open-file")
def open_file(req: OpenReq):
    if req.kind != "file":
        raise HTTPException(400, "kind 必须为 file")
    p = Path(os.path.expanduser(req.path))
    if not p.exists() or not p.is_file():
        raise HTTPException(404, f"文件不存在: {req.path}")
    if not h5inspector.is_h5(p.name):
        raise HTTPException(400, f"不是 h5/hdf5 文件: {p.name}")
    info = h5inspector.inspect_h5_file(str(p))
    if info.get("error"):
        raise HTTPException(400, f"读取失败: {info['error']}")
    C.save_recent_path(str(p))
    return info


@app.get("/api/recent")
def recent():
    return {"paths": C.load_recent_paths()}


@app.get("/api/home")
def home():
    """家目录（默认浏览起点；打包后不写死任何本机路径）。"""
    return {"path": str(Path.home())}


@app.get("/api/cmaps")
def cmaps():
    """常用连续色板采样色值（8 点）+ 内置预设色值，供前端显示颜色预览条。"""
    try:
        import matplotlib.cm as _cm
        from matplotlib.colors import to_hex
        out = {}
        for name in C.COLORMAPS["sequential"]:
            try:
                cmap = _cm.get_cmap(name)
                out[name] = [to_hex(cmap(i / 7.0)) for i in range(8)]
            except Exception:  # noqa: BLE001
                pass
        for preset in C.COLORMAPS["qualitative"]:
            vals = preset.get("values")
            if vals:
                out[preset["name"]] = list(vals)
        return {"cmaps": out}
    except Exception as e:  # noqa: BLE001
        return {"cmaps": {}, "error": str(e)}


@app.post("/api/step-scan")
def step_scan(req: OpenReq):
    """扫描模型输出目录，返回时间步与可用字段（用于时间自动对齐）。"""
    if req.kind != "dir":
        raise HTTPException(400, "kind 必须为 dir")
    out = h5inspector.scan_model_dir(req.path)
    if out.get("error"):
        raise HTTPException(400, out["error"])
    return out


# --------------------------------------------------------------------------
# 绘图
# --------------------------------------------------------------------------
class PlotReq(BaseModel):
    orientation: str = "portrait"
    style: dict = {}
    panels: list[dict]
    engine: str = "matplotlib"   # matplotlib | rust (plotkit sidecar)


@app.post("/api/plot")
def make_plot(req: PlotReq):
    try:
        d = req.model_dump()
        if d.get("engine") == "rust":
            from core import rust_engine
            if (rust_engine.rust_available() and len(d.get("panels") or []) == 1
                    and (d["panels"][0].get("kind") == "material")):
                import secrets as _s
                return rust_engine.render_material_rust(d["panels"][0], _s.token_hex(6),
                                                        dpi=int(d.get("style", {}).get("png_dpi", 300)))
        from core import plotters
        meta = plotters.render_plot(d)
        return meta
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"绘图失败: {e}") from e


@app.get("/api/plots/{plot_id}.{suffix}")
def plot_asset(plot_id: str, suffix: str):
    allowed = {"png", "pdf", "svg", "json"}
    if suffix not in allowed and not suffix.endswith(".png300.png"):
        raise HTTPException(400, "不支持的格式")
    name = "png300.png" if suffix.endswith(".png300.png") else suffix
    p = C.PLOT_DIR / f"{plot_id}.{name}"
    if not p.exists():
        # svg/pdf/png300 延迟生成（提速：首次渲染只出预览 png）
        if name in ("pdf", "png300.png", "svg"):
            from core import plotters
            if plotters.ensure_hi_res(plot_id):
                p = C.PLOT_DIR / f"{plot_id}.{name}"
            else:
                raise HTTPException(404, "渲染产物不存在")
    return FileResponse(str(p))


class ProbeReq(BaseModel):
    plot_id: str
    px_x: float
    px_y: float
    fig_w_px: float
    fig_h_px: float


@app.post("/api/probe")
def do_probe(req: ProbeReq):
    try:
        from core import probe
        return probe.probe(req.plot_id, req.px_x, req.px_y,
                          req.fig_w_px, req.fig_h_px)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"探针失败: {e}") from e


class ExportReq(BaseModel):
    plot_id: str
    dest_dir: str
    basename: str | None = None


@app.post("/api/export")
def export_plot(req: ExportReq):
    """导出 A4 三件套（PNG300 / PDF / SVG）到用户指定目录。"""
    dest = Path(os.path.expanduser(req.dest_dir))
    if not dest.exists():
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise HTTPException(400, f"无法创建导出目录: {e}") from e
    if not dest.is_dir():
        raise HTTPException(400, "导出目标不是目录")
    from core import plotters
    meta = plotters.get_meta(req.plot_id)
    if meta is None:
        raise HTTPException(404, "plot 不存在")
    # 确保高分辨率产物存在（按需渲染，含 pdf/png300）
    if not plotters.ensure_hi_res(req.plot_id):
        raise HTTPException(500, "高分辨率产物生成失败")
    base = req.basename or Path(meta["panels"][0].get("file") or "plot").stem if meta.get("panels") else "plot"
    if not req.basename and meta.get("panels"):
        base = Path(meta["panels"][0].get("file") or "plot").stem
    base = Path(base).stem
    writes = {}
    for suffix, src_name in [("png", "png300.png"), ("pdf", "pdf"), ("svg", "svg")]:
        src = C.PLOT_DIR / f"{req.plot_id}.{src_name}"
        if src.exists():
            dst = dest / f"{base}.{suffix}"
            shutil.copy2(src, dst)
            writes[suffix] = str(dst)
    return {"wrote": writes}


# --------------------------------------------------------------------------
# 配置记忆
# --------------------------------------------------------------------------
@app.get("/api/config")
def get_config():
    return C.load_config()


class ConfigReq(BaseModel):
    config: dict


@app.post("/api/config")
def save_config(req: ConfigReq):
    C.save_config(req.config)
    return {"ok": True}


@app.post("/api/clear-rendered")
def clear_rendered():
    C.clear_rendered()
    return {"ok": True}