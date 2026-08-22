"""点击探针（probe）：像素坐标 → 数据坐标 → 最近数据点读数。

渲染时每个 panel 已保存 axes 像素 bbox 与数据范围（plotters.render_plot）。
probe 数据懒构建（首次探针时读取/下采样原始 h5 并缓存为 npz），
避免每次渲染都付出大文件读取代价。

坐标约定：前端把 SVG/预览 PNG 的像素坐标（y 向下）传进来；后端换算时
y 翻转为 matplotlib 窗口坐标（y 向上，原点在 figure 左下）。
"""
from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np

from . import config as C

PLOT_DIR = C.PLOT_DIR
MAX_PROBE_POINTS = 150_000


def _load_meta(plot_id: str) -> dict:
    p = PLOT_DIR / f"{plot_id}.json"
    if not p.exists():
        raise FileNotFoundError(f"plot {plot_id} 不存在")
    return json.loads(p.read_text("utf-8"))


def ensure_cache(plot_id: str) -> Path:
    """懒构建 probe 数据缓存（npz），返回缓存文件路径。"""
    npz = PLOT_DIR / f"{plot_id}.probe.npz"
    if npz.exists():
        return npz
    meta = _load_meta(plot_id)
    payload: dict[str, np.ndarray] = {}
    for panel in meta.get("panels", []):
        i = panel["i"]
        kind = panel["kind"]
        fn = panel.get("file", "")
        dsname = panel.get("dataset", "data")
        if not fn or not Path(fn).exists():
            continue
        try:
            if kind == "field":
                with h5py.File(fn, "r") as f:
                    ds = f[dsname]
                    if ds.ndim == 1:
                        vals = ds[:]
                    else:
                        vals = ds[:, 0]
                vals = np.asarray(vals, dtype=float)
                X = Y = None
                mesh_file = panel.get("mesh_file")
                if mesh_file and Path(mesh_file).exists():
                    from .plotters import _mesh_geometry, _field_grid
                    verts, geo = _mesh_geometry(mesh_file)
                    X, Y, _ = _field_grid(verts, geo)
                    try:
                        vals = vals.reshape(X.shape)
                    except ValueError:
                        X = Y = None
                if X is None:
                    n = vals.size
                    ny = int(round(n ** 0.5))
                    nx = n // ny if ny else 1
                    while nx > 0 and nx * ny != n:
                        ny -= 1
                        if ny <= 0:
                            nx = n; ny = 1; break
                        nx = n // ny if ny else 1
                    Z = vals[: nx * ny].reshape(ny, nx)
                    X = np.arange(nx + 1) - 0.5
                    Y = np.arange(ny + 1) - 0.5
                    vals = Z
                else:
                    vals = vals.reshape(X.shape)
                payload[f"p{i}_type"] = np.array("field")
                payload[f"p{i}_x"] = X[0] if X.ndim == 2 else X
                payload[f"p{i}_y"] = Y[:, 0] if Y.ndim == 2 else Y
                payload[f"p{i}_v"] = vals
                payload[f"p{i}_names"] = np.array(["value"])
            elif kind == "swarm":
                with h5py.File(fn, "r") as f:
                    xy = f[dsname][:].astype(float)
                import numpy as _np
                xc = panel.get("x_col") or 0
                yc = panel.get("y_col") or 1
                x = xy[:, int(xc)]
                y = xy[:, int(yc)]
                n = len(x)
                if n > MAX_PROBE_POINTS:
                    rng = _np.random.default_rng(5)
                    idx = rng.choice(n, MAX_PROBE_POINTS, replace=False)
                    x, y = x[idx], y[idx]
                values = y  # 默认给 y；有数值列则给该列
                payload[f"p{i}_type"] = np.array("swarm")
                payload[f"p{i}_x"] = x
                payload[f"p{i}_y"] = y
                payload[f"p{i}_v"] = values
                payload[f"p{i}_names"] = np.array(["y"])
            elif kind in ("material",):
                # 材质场探针：swarm 坐标 + 最近粒子的材料 id / 设色值
                with h5py.File(fn, "r") as f:
                    xy = f[dsname][:].astype(float)
                xc = panel.get("x_col") or 0
                yc = panel.get("y_col") or 1
                x = xy[:, int(xc)]
                y = xy[:, int(yc)]
                n = len(x)
                mfile = panel.get("material_file") or fn
                if mfile and Path(mfile).exists():
                    with h5py.File(mfile, "r") as f:
                        mat = np.asarray(f[panel.get("material_dataset", "data")][:],
                                         dtype=int).reshape(-1)[:n]
                else:
                    mat = np.ones(n, dtype=int)
                if n > MAX_PROBE_POINTS:
                    rng = np.random.default_rng(5)
                    idx = rng.choice(n, MAX_PROBE_POINTS, replace=False)
                    x, y, mat = x[idx], y[idx], mat[idx]
                payload[f"p{i}_type"] = np.array("material")
                payload[f"p{i}_x"] = np.asarray(x)
                payload[f"p{i}_y"] = np.asarray(y)
                payload[f"p{i}_v"] = np.asarray(mat, dtype=int)
                names = np.array(["material"])
                payload[f"p{i}_names"] = names
            elif kind == "curve":
                with h5py.File(fn, "r") as f:
                    ds = f[dsname]
                    n = ds.shape[0]
                    if n > 400_000:
                        # 分段块读（避免随机索引）
                        seg = 133_333
                        pieces = [ds[:seg], ds[n // 2:n // 2 + seg], ds[n - seg:]]
                        try:
                            arr = np.concatenate(pieces)
                        except ValueError:
                            arr = ds[:]
                    else:
                        arr = ds[:]
                arr = np.asarray(arr)
                if arr.ndim == 1:
                    arr = arr[:, None]
                x = np.arange(arr.shape[0])
                if panel.get("x_column") is not None:
                    x = arr[:, int(panel["x_column"])]
                payload[f"p{i}_type"] = np.array("curve")
                payload[f"p{i}_x"] = x
                payload[f"p{i}_y"] = arr
                payload[f"p{i}_names"] = np.array([f"col{n}" for n in range(arr.shape[1])])
        except Exception:  # noqa: BLE001
            continue
    np.savez_compressed(npz, **payload)
    return npz


def _data_from_px(panel: dict, px_x: float, px_y: float,
                  fig_w_px: float, fig_h_px: float) -> tuple[float, float]:
    """前端像素（y 向下）→ 数据坐标。"""
    x0, y0 = panel["x0_px"], panel["y0_px"]
    w, h = panel["w_px"], panel["h_px"]
    cx = (px_x - x0) / w
    cy = 1 - (px_y - y0) / h                      # y 翻转
    xlim = panel.get("xlim", [0, 1])
    ylim = panel.get("ylim", [0, 1])
    if panel.get("xscale") == "log":
        dx = xlim[0] * (xlim[1] / xlim[0]) ** cx
    else:
        dx = xlim[0] + (xlim[1] - xlim[0]) * cx
    if panel.get("yscale") == "log":
        dy = ylim[0] * (ylim[1] / ylim[0]) ** cy
    else:
        dy = ylim[0] + (ylim[1] - ylim[0]) * cy
    return float(dx), float(dy)


def probe(plot_id: str, px_x: float, px_y: float,
          fig_w_px: float, fig_h_px: float) -> dict:
    """返回点击处数据读数：坐标、所在面板、最近点值。"""
    meta = _load_meta(plot_id)
    cache = ensure_cache(plot_id)
    data = np.load(cache, allow_pickle=False)

    best = None
    for panel in meta.get("panels", []):
        i = panel["i"]
        # meta bbox 为 matplotlib 底原点坐标；前端点击为顶原点 → 统一翻转为顶原点
        pp = dict(panel)
        pp["y0_px"] = fig_h_px - panel["y0_px"] - panel["h_px"]
        x0, y0 = pp["x0_px"], pp["y0_px"]
        if px_x < x0 or px_x > x0 + pp["w_px"]:
            continue
        if px_y < y0 or px_y > y0 + pp["h_px"]:
            continue
        try:
            dx, dy = _data_from_px(pp, px_x, px_y, fig_w_px, fig_h_px)
        except Exception:  # noqa: BLE001
            continue
        ptype = str(data[f"p{i}_type"]) if f"p{i}_type" in data else ""
        msg = {"panel": i, "kind": panel["kind"], "x": dx, "y": dy, "values": {}}
        if ptype == "field":
            xs = data[f"p{i}_x"][0] if data[f"p{i}_x"].ndim > 1 else data[f"p{i}_x"]
            ys = data[f"p{i}_y"][:, 0] if data[f"p{i}_y"].ndim > 1 else data[f"p{i}_y"]
            v = data[f"p{i}_v"]
            ix = int(np.argmin(np.abs(xs - dx)))
            iy = int(np.argmin(np.abs(ys - dy)))
            if v.ndim == 2 and 0 <= ix < v.shape[1] and 0 <= iy < v.shape[0]:
                msg["values"]["value"] = round(float(v[iy, ix]), 6)
                msg["x"] = round(float(xs[ix]), 4)
                msg["y"] = round(float(ys[iy]), 4)
            elif v.ndim == 1:
                msg["values"]["value"] = round(float(v[iy]), 6)
        elif ptype in ("swarm", "material"):
            from scipy.spatial import cKDTree
            xs, ys = data[f"p{i}_x"], data[f"p{i}_y"]
            tree = cKDTree(np.c_[xs, ys])
            d, k = tree.query([dx, dy], k=1)
            if ptype == "material":
                mat = int(data[f"p{i}_v"][k])
                msg["values"]["material"] = mat
                msg["values"]["mat_name"] = C.MATERIAL_NAMES.get(mat, f"mat {mat}")
            else:
                msg["values"]["nearest"] = round(float(data[f"p{i}_v"][k]), 6)
            msg["dist"] = round(float(d), 4)
            msg["x"] = round(float(xs[k]), 4)
            msg["y"] = round(float(ys[k]), 4)
            msg["values"]["nearest_index"] = int(k)
        elif ptype == "curve":
            xs = data[f"p{i}_x"]
            yv = data[f"p{i}_y"]
            k = int(np.argmin(np.abs(xs - dx)))
            msg["x"] = round(float(xs[k]), 6)
            msg["values"] = {}
            names = data.get(f"p{i}_names", [])
            if yv.ndim == 1:
                msg["values"][str(names[0]) if len(names) else "y"] = round(float(yv[k]), 6)
            else:
                for c in range(yv.shape[1]):
                    key = str(names[c]) if len(names) > c else f"col{c}"
                    msg["values"][key] = round(float(yv[k, c]), 6)
        best = msg
        break
    if best is None:
        return {"hit": False}
    best["hit"] = True
    return best