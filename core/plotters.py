"""A4 画板绘图引擎：field / swarm / curve 三类模板，matplotlib 与 ultraplot 双渲染。

渲染结果（预览 PNG + 可编辑 SVG + 出版 PDF/PNG300dpi + probe 数据）统一存到
userdata/rendered/{plot_id}.*，前端通过 /api/plots/{plot_id}.{fmt} 取用。

probe 数据：每个 panel 保存 axes 像素 bbox（dpi=100 基准）与降采样数据（npz），
点击 → 前端像素 → 数据坐标 → 最近数据点读数（core/probe.py）。
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import config as C

MAX_SWARM_POINTS = 200_000   # 粒子图自动下采样上限
STATS_SAMPLE = 400_000
PREVIEW_DPI = 300            # 预览 PNG 分辨率（屏幕大图清晰；probe bbox 以此为基准）

PLOT_DIR = C.PLOT_DIR
SUBSAMPLE_CACHE = PLOT_DIR / "subcache"
SUBSAMPLE_CACHE.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# 工具
# --------------------------------------------------------------------------
def _read(fn: str, key: str = "data") -> np.ndarray:
    with h5py.File(fn, "r") as f:
        return f[key][:]


def _auto_index(ds_name: str) -> int | None:
    """'temperature-160' -> 160；用于多步文件读取判断。"""
    import re
    m = re.search(r"-(\d+)(?:\.[^.]+)?$", ds_name)
    return int(m.group(1)) if m else None


def _apply_style(ax, style: dict, hidden=("top", "right")) -> None:
    ax.tick_params(axis="both", labelsize=style.get("tick_size", 7),
                   direction=style.get("tick_direction", "in"), length=3,
                   width=style.get("axes_linewidth", 0.75))
    for s in hidden:
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_linewidth(style.get("axes_linewidth", 0.75))
    ax.set_xlabel(ax.get_xlabel(), fontsize=style.get("axes_label_size", 8))
    ax.set_ylabel(ax.get_ylabel(), fontsize=style.get("axes_label_size", 8))
    if ax.get_title():
        ax.set_title(ax.get_title(), fontsize=style.get("title_size", 8))


def _categorical_cmap(values: list[str] | None):
    if values:
        return matplotlib.colors.ListedColormap(values)
    return plt.get_cmap("tab10")


def _material_lookup(cmap_values: list[str] | None):
    """按材料 id 查颜色：列表/预设按 id=1..N 排列（index=id-1），越界灰色。

    与用户 Myfig_4steps.py 一致：1=Air 白, 2=Sed 黄, 3=LM, 4..9 等，
    **不能用 mat % len 索引**（会整体错位一位）。
    """
    vals = list(cmap_values or C.QAIDAM_MATERIAL_COLORS.values())
    n = max(30, len(vals) + 1)
    table = ["#888888"] * n
    for i, c in enumerate(vals):
        if i + 1 < n:
            table[i + 1] = c
    def lookup(mid) -> str:
        i = int(mid)
        return table[i] if 0 <= i < n else "#888888"
    return lookup


def _mesh_geometry(mesh_file: str) -> tuple[np.ndarray, np.ndarray, dict]:
    """mesh.h5 → 规则网格 X/Y 坐标（未 reshapeael 版本返回原始）。"""
    with h5py.File(mesh_file, "r") as f:
        verts = f["vertices"][:]
        minxy = np.asarray(f.attrs.get("min", [0, 0]), dtype=float)
        maxxy = np.asarray(f.attrs.get("max", [1, 1]), dtype=float)
        res = np.asarray(f.attrs.get("mesh resolution",
                                     f.attrs.get("regular", [1, 1])), dtype=int)
        if res.shape == ():
            res = np.asarray([1, 1])
        if res.size < 2:
            res = np.asarray([res[0], 1])
    nx, ny = int(res[0]), int(res[1])
    return verts, {"min": minxy, "max": maxxy, "nx": nx, "ny": ny}


def _field_grid(verts: np.ndarray, geo: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    nx, ny = geo["nx"], geo["ny"]
    try:
        X = verts[:, 0].reshape(ny + 1, nx + 1)
        Y = verts[:, 1].reshape(ny + 1, nx + 1)
    except ValueError:
        # 非规则顺序：用规则坐标网格近似（平面）
        xs = np.linspace(geo["min"][0], geo["max"][0], nx + 1)
        ys = np.linspace(geo["min"][1], geo["max"][1], ny + 1)
        X, Y = np.meshgrid(xs, ys)
    return X, Y, verts


def _downsample_swarm(xy: np.ndarray, n: int = MAX_SWARM_POINTS,
                      seed: int = 42) -> np.ndarray:
    if len(xy) <= n:
        return xy
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(xy), n, replace=False)
    return xy[idx]


def _subsample_with_cache(fn: str, mat_fn: str | None = None,
                          max_pts: int = MAX_SWARM_POINTS,
                          seed: int = 11) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    """读 swarm 坐标（+材料）并下采样；结果按文件大小+mtime 磁盘缓存，重复渲染秒开。

    返回 (xy 下采样数组, mat 下采样数组或 None, 采样索引 idx 或 None)。
    idx 供叠加层（如 plasticStrain 粒子场）按同一索引对齐取值。
    """
    import hashlib
    key = f"m{max_pts}:{os.path.getsize(fn)}:{os.path.getmtime(fn)}"
    if mat_fn:
        key += f":{os.path.getsize(mat_fn)}:{os.path.getmtime(mat_fn)}"
    h = hashlib.sha1((fn + key).encode("utf-8")).hexdigest()[:16]
    cache = SUBSAMPLE_CACHE / f"{h}.npz"
    if cache.exists():
        try:
            z = np.load(cache, allow_pickle=False)
            idx = z["idx"] if "idx" in z else None
            return z["xy"], (z["mat"] if "mat" in z else None), idx
        except Exception:  # noqa: BLE001
            pass
    with h5py.File(fn, "r") as f:
        xy = f["data"][:].astype(float)
    n = len(xy)
    idx = None
    if n > max_pts:
        rng = np.random.default_rng(seed)
        idx = rng.choice(n, max_pts, replace=False)
        xy = xy[idx]
    mat = None
    if mat_fn and Path(mat_fn).exists():
        with h5py.File(mat_fn, "r") as f:
            mat = np.asarray(f["data"][:], dtype=int).reshape(-1)
        if idx is not None:
            mat = mat[idx]
        else:
            mat = mat[:n]
    try:
        if mat is not None:
            np.savez_compressed(cache, xy=xy, mat=mat, idx=idx if idx is not None else np.array([]))
        else:
            np.savez_compressed(cache, xy=xy, idx=idx if idx is not None else np.array([]))
    except OSError:
        pass
    return xy, mat, idx


# --------------------------------------------------------------------------
# 叠加层公共工具
# --------------------------------------------------------------------------
def _overlay_vectors(ax, ov: dict, ofile: str, style: dict) -> None:
    """速度矢量叠加（quiver）：读网格节点二维速度 (ux, uy)，稀疏化后画箭头。

    参数：
      stride      -> 每 n 个节点取 1 个箭头（默认自动，使总数 <= 800）
      scale       -> quiver scale（箭头长度缩放，默认自动）
      color       -> 箭头颜色（默认白色；设 "speed" 时按速度大小着色）
      cmap        -> color="speed" 时用的色板
      width       -> 箭头线宽（pt）
      alpha       -> 透明度
      key_uv      -> 参考箭头大小（如 2 表示 2 cm/yr），需同时给 scale 才精确
      key_text    -> 参考箭头标签
      colorbar    -> color="speed" 时显示 colorbar
      cbar_label  -> colorbar 标签
    """
    with h5py.File(ofile, "r") as f:
        arr = f[ov.get("dataset", "data")][:]
    arr = np.asarray(arr, dtype=float)
    if arr.ndim == 1:
        if ov.get("column") is not None:
            # 单列速度大小（无方向）退化为场叠加
            raise ValueError("速度文件应为两列 (ux, uy)；单列请改用场叠加")
        arr = arr[:, None]
    if arr.shape[1] < 2:
        raise ValueError(f"速度矢量需要至少两列 (ux, uy)，实际 {arr.shape[1]} 列")
    u = arr[:, int(ov.get("ux_col", 0))]
    v = arr[:, int(ov.get("uy_col", 1))]
    # 过滤非有限值（NaN/inf 会让 quiver 自动 scale 崩溃）
    good = np.isfinite(u) & np.isfinite(v)
    u = u[good]
    v = v[good]
    mesh_file = ov.get("mesh_file") or _guess_mesh_file(ofile)
    if not mesh_file or not Path(mesh_file).exists():
        raise ValueError("缺少 mesh.h5（速度叠加需要网格几何）")
    verts, geo = _mesh_geometry(mesh_file)
    X, Y, _ = _field_grid(verts, geo)
    if u.size != X.size:
        raise ValueError(f"{ofile} 节点数 {u.size} 与网格 {X.size} 不匹配")
    U = u.reshape(X.shape)
    V = v.reshape(X.shape)
    # 稀疏化（默认约 150 个箭头，避免遮盖底层材料场）
    if ov.get("stride"):
        s = max(1, int(ov["stride"]))
    else:
        ntot = X.size
        s = max(1, int(np.ceil(np.sqrt(ntot / 150))))
    U, V = U[::s, ::s], V[::s, ::s]
    XX, YY = X[::s, ::s], Y[::s, ::s]
    speed = np.hypot(U, V)
    # 默认 scale 显式计算：95 分位速度对应的箭头约为轴宽（x 方向）的 1%
    if ov.get("scale") is not None and float(ov["scale"]) > 0:
        scale = float(ov["scale"])
    else:
        v95 = float(np.nanpercentile(speed, 95)) if speed.size else 1.0
        xspan = float(XX.max() - XX.min()) or 1.0
        scale = max(v95, 1e-12) / (0.01 * xspan)
    color_mode = str(ov.get("color", "#FFFFFF")).lower()
    # width 为相对图宽比例（matplotlib quiver 惯例：默认 0.005 = 0.5%），
    # 前端 0.005 对应细箭头；若传入 >0.1 视为误传的 pt 语义，归一化
    w = float(ov.get("width", 0.005))
    if w > 0.1:
        w /= 100.0
    kw = dict(scale=scale,
              scale_units="xy",
              width=w,
              alpha=float(ov.get("alpha", 0.9)),
              pivot=ov.get("pivot", "mid"), rasterized=True)
    if color_mode == "speed":
        norm = None
        if ov.get("vmin") is not None or ov.get("vmax") is not None:
            norm = matplotlib.colors.Normalize(
                vmin=float(ov.get("vmin", speed.min())),
                vmax=float(ov.get("vmax", speed.max())))
        q = ax.quiver(XX, YY, U, V, speed, cmap=ov.get("cmap", "turbo"),
                      norm=norm, **kw)
        if ov.get("colorbar", False):
            cb = ax.figure.colorbar(q, ax=ax, **(_colorbar_kw(ov) or dict(fraction=0.046, pad=0.04)))
            cb.ax.tick_params(labelsize=style.get("tick_size", 7))
            if ov.get("cbar_label"):
                cb.set_label(ov["cbar_label"],
                             fontsize=style.get("axes_label_size", 8))
    else:
        q = ax.quiver(XX, YY, U, V, color=color_mode, **kw)
    # 参考箭头
    if ov.get("key_uv") is not None:
        ax.quiverkey(q, float(ov.get("key_x", 0.02)), float(ov.get("key_y", 0.98)),
                     float(ov["key_uv"]), ov.get("key_text", f"{ov['key_uv']} cm/yr"),
                     labelpos="E",
                     color="#FFFFFF" if color_mode != "speed" else None)


def _overlay_tracers(ax, ov: dict, ofile: str, style: dict) -> None:
    """被动追踪点叠加：读 swarm/tracer 文件坐标，叠加在任意面板上。

    支持单个文件或 files 列表（多组追踪点，如 grid1..gridN），
    多组时按 color_cycle 依次着色。
    """
    files = ov.get("files") or [ofile]
    files = [f for f in files if f and Path(f).exists()]
    if not files:
        raise ValueError("追踪点文件不存在")
    colors = ov.get("colors") or [ov.get("color") or "#FFD700"]
    marker = ov.get("marker", "o")
    size = float(ov.get("size", 1.0))
    alpha = float(ov.get("alpha", 0.9))
    xc = int(ov.get("x_col", 0))
    yc = int(ov.get("y_col", 1))
    maxpts = int(ov.get("max_points", MAX_SWARM_POINTS))
    for fi, fn in enumerate(files):
        with h5py.File(fn, "r") as f:
            xy = f[ov.get("dataset", "data")][:].astype(float)
        if xy.ndim == 1:
            xy = xy[:, None]
        if xy.shape[1] <= max(xc, yc):
            continue
        tx, ty = xy[:, xc], xy[:, yc]
        n = len(tx)
        if n == 0:
            continue
        if n > maxpts:
            rng = np.random.default_rng(13)
            idx = rng.choice(n, maxpts, replace=False)
            tx, ty = tx[idx], ty[idx]
        color = colors[fi % len(colors)]
        lbl = None
        if ov.get("labels") and fi < len(ov["labels"]):
            lbl = ov["labels"][fi]
        elif ov.get("label"):
            lbl = ov["label"]
        ax.scatter(tx, ty, s=size, marker=marker, color=color, alpha=alpha,
                   edgecolors=ov.get("edgecolors", "none"),
                   linewidths=float(ov.get("edge_width", 0.4)),
                   label=lbl,
                   rasterized=True, antialiased=False)
    # 图例（多组时有意义）
    if ov.get("legend", False) and (ov.get("labels") or len(files) > 1):
        import matplotlib.patches as mpatches
        labels = ov.get("labels") or [Path(f).stem for f in files]
        handles = [mpatches.Patch(facecolor=colors[i % len(colors)],
                                  edgecolor=ov.get("edgecolors", "none"),
                                  label=labels[i])
                   for i in range(min(len(files), len(labels)))]
        ax.legend(handles=handles, fontsize=style.get("legend_size", 6.5),
                  frameon=False, **_legend_kw(ov))


# --------------------------------------------------------------------------
# 各面板绘制
# --------------------------------------------------------------------------
def _resolve_cmap(panel: dict, discrete: bool = False, default: str = "turbo"):
    """解析色板：内置预设（cmap_values 颜色列表）或 matplotlib 名称色板。

    discrete=True（材料/分类）用 ListedColormap；连续场用 from_list 平滑插值。
    """
    vals = panel.get("cmap_values")
    if vals:
        cm = (matplotlib.colors.ListedColormap(vals) if discrete
              else matplotlib.colors.LinearSegmentedColormap.from_list("preset", vals, 256))
        return cm.reversed() if panel.get("cmap_reverse") else cm
    from .qgis_cmaps import get_cmap as _qgis_cmap
    q = _qgis_cmap(panel.get("cmap", ""))
    cm = q if q is not None else plt.get_cmap(panel.get("cmap", default))
    # 反转色板（matplotlib *_r 同效）
    if panel.get("cmap_reverse"):
        try:
            cm = cm.reversed()
        except Exception:  # noqa: BLE001
            pass
    return cm


def _apply_axes_common(ax, panel: dict) -> None:
    """面板通用轴选项：网格线、log 坐标、spines、刻度方向等（全部 UI 可选）。"""
    if panel.get("grid"):
        ax.grid(True, color=panel.get("grid_color", "#CCCCCC"),
                ls=panel.get("grid_ls", "--"),
                lw=float(panel.get("grid_lw", 0.4)),
                alpha=float(panel.get("grid_alpha", 0.5)))
    else:
        ax.grid(False)
    if panel.get("xscale_log"):
        ax.set_xscale("log")
    if panel.get("yscale_log"):
        ax.set_yscale("log")
    if panel.get("spines_all"):
        for s in ("top", "right"):
            ax.spines[s].set_visible(True)


def _colorbar_kw(panel: dict, ov: dict | None = None) -> dict:
    """colorbar 参数（位置/大小/填充）——面板与叠加层可各自配置。"""
    src = panel if ov is None else ov
    kw = {}
    loc = src.get("cb_location")
    if loc:
        kw["location"] = loc
    fr = src.get("cb_fraction")
    if fr is not None:
        kw["fraction"] = float(fr)
    pad = src.get("cb_pad")
    if pad is not None:
        kw["pad"] = float(pad)
    return kw


def _legend_kw(panel: dict) -> dict:
    """图例参数：'outside right/bottom' → axes 外侧（仍在 A4 画板内，不遮挡数据）。"""
    loc = panel.get("legend_loc", "best")
    if loc == "outside right":
        return dict(bbox_to_anchor=(1.02, 0.5), loc="center left", borderaxespad=0.0)
    if loc == "outside bottom":
        # 初始锚点；_fix_outside_bottom_legend 会按 xlabel+ticks 实际占位精确下移
        return dict(bbox_to_anchor=(0.5, -0.08), loc="upper center", borderaxespad=0.0)
    return dict(loc=loc)


def _cb_tight_bbox(fig, cbax):
    """colorbar 完整占位（含刻度与标签），figure 坐标。"""
    r = fig.canvas.renderer
    bb = cbax.get_tightbbox(r)
    return bb.transformed(fig.transFigure.inverted()) if bb is not None else None


def _fix_outside_right_legend(fig, ax, cell=None) -> None:
    """外右图例：只用自己单元内的右隙（colorbar 之后）；放不下回退外底（不侵入邻面板）。"""
    leg = ax.get_legend()
    if leg is None:
        return
    cell = cell or ax.get_position()
    fig.canvas.draw()
    r = fig.canvas.renderer
    inv = fig.transFigure.inverted()
    lb = leg.get_window_extent(r).transformed(inv)
    pos = ax.get_position()
    x0_avail = pos.x1
    cbax = getattr(ax, "_h5_cb_ax", None)
    if cbax is not None:
        cbb = _cb_tight_bbox(fig, cbax) or cbax.get_position()
        if cbb.x0 >= pos.x1 - 0.001:   # colorbar 在右
            x0_avail = cbb.x1
    gap = 0.010
    if x0_avail + gap + lb.width <= cell.x1 - 0.002:
        leg.set_bbox_to_anchor(((x0_avail + gap - pos.x0) / max(pos.width, 1e-6), 0.5))
    else:
        handles, labels = ax.get_legend_handles_labels()
        leg.remove()
        if handles:
            ax.legend(handles, labels, **_legend_kw({"legend_loc": "outside bottom"}))
            _fix_outside_bottom_legend(fig, ax, cell)


def _fix_outside_bottom_legend(fig, ax, cell=None) -> None:
    """外底图例：只在自己的网格单元内腾空间（axes 上移，底部留出
    “x 轴占位 + 图例”条带；底部 colorbar 存在时条带在其上方）——不侵入相邻面板。"""
    leg = ax.get_legend()
    if leg is None:
        return
    cell = cell or ax.get_position()
    fig.canvas.draw()
    r = fig.canvas.renderer
    pos = ax.get_position()
    fig_h = fig.bbox.height
    xb = ax.xaxis.get_tightbbox(r)
    hX = (xb.height / fig_h) if xb is not None else 0.05
    hL = leg.get_window_extent(r).height / fig_h
    gap = 0.010
    bottom_limit = cell.y0
    cbax = getattr(ax, "_h5_cb_ax", None)
    if cbax is not None:
        cbb = _cb_tight_bbox(fig, cbax) or cbax.get_position()
        if cbb.y1 <= pos.y0 + 0.02:
            bottom_limit = max(bottom_limit, cbb.y1)
    needed_y0 = bottom_limit + gap + hL + gap + hX
    if pos.y0 < needed_y0:
        ax.set_position([pos.x0, needed_y0, pos.width,
                         max(pos.y1 - needed_y0, 0.05)])
        pos = ax.get_position()
    # 图例顶边锚到 x 轴占位区之下（占位区悬挂于新 axes 底边下方 hX）
    desired_top = pos.y0 - hX - gap
    leg.set_bbox_to_anchor((0.5, (desired_top - pos.y0) / max(pos.height, 1e-6)))


BOX_RATIOS = {"4:3": 4 / 3, "16:9": 16 / 9}


def _apply_box_ratio(ax, cell, ratio: float) -> None:
    """盒比例预设（4:3 / 16:9）：在网格单元内居中适配出目标物理宽高比的 axes。"""
    W, H = ax.get_figure().get_size_inches()
    cw, ch = cell.width * W, cell.height * H   # 物理英寸
    if cw / ch > ratio:
        h = ch
        w = h * ratio
    else:
        w = cw
        h = w / ratio
    wf, hf = w / W, h / H
    ax.set_position([cell.x0 + (cell.width - wf) / 2,
                     cell.y0 + (cell.height - hf) / 2, wf, hf])


def _apply_aspect(ax, panel: dict) -> None:
    """面板横纵比：'equal'/数字（y 相对 x 拉伸倍）/'auto'。

    equal = 数据等比（如 x 0-800km / y -150-10km → 面板显示 5:1 横条）。
    """
    a = panel.get("aspect")
    if a in ("equal", "data", "1") or a is True:
        ax.set_aspect(1.0, adjustable="box")
    elif isinstance(a, (int, float)) and not isinstance(a, bool) and float(a) > 0:
        ax.set_aspect(float(a), adjustable="box")
    elif a in ("auto", None):
        pass
    else:
        try:
            ax.set_aspect(float(a), adjustable="box")
        except (TypeError, ValueError):
            pass


def _draw_material_fast(ax, panel: dict, style: dict) -> dict:
    """物质场快速模式：粒子按规则网格多数投票 → imshow（0.3s 级 vs 散点 3s+）。

    panel['fast']=True 时启用；fast_res=[nx, ny] 可调网格分辨率（默认 1200×240）。
    视觉近似散点图，适合快速迭代排版；最终出图可关掉回到散点模式。
    """
    fn = panel["file"]
    mfile = panel.get("material_file") or fn
    xy, mat, idx = _subsample_with_cache(fn, mfile if mfile and Path(mfile).exists() else None)
    if mat is None:
        mat = np.ones(len(xy), dtype=int)
    x, y = xy[:, int(panel.get("x_col", 0))], xy[:, int(panel.get("y_col", 1))]
    only_mats = panel.get("only_materials")
    if only_mats:
        keep = np.isin(mat, [int(v) for v in only_mats])
        x, y, mat = x[keep], y[keep], mat[keep]
    bg = panel.get("bg_color")
    if bg:
        ax.set_facecolor(bg)
    fr = panel.get("fast_res") or [800, 160]
    nx, ny = int(fr[0]), int(fr[1])
    x0, x1 = panel.get("xlim") or [float(x.min()), float(x.max())]
    y0, y1 = panel.get("ylim") or [float(y.min()), float(y.max())]
    if x1 <= x0 or y1 <= y0:
        x0, x1 = float(x.min()), float(x.max())
        y0, y1 = float(y.min()), float(y.max())
    ix = np.clip(((x - x0) / (x1 - x0) * nx).astype(np.int32), 0, nx - 1)
    iy = np.clip(((y - y0) / (y1 - y0) * ny).astype(np.int32), 0, ny - 1)
    bin_id = (iy * nx + ix).astype(np.int64)
    uniq = np.unique(mat)
    cnts = np.zeros((ny * nx, len(uniq)), dtype=np.int32)
    for i, m in enumerate(uniq):
        cnts[:, i] = np.bincount(bin_id[mat == m], minlength=ny * nx)
    # 密度合成：每 bin 各材料计数 → 材料色×密度 alpha 逐层叠加（保留散点密度质感）
    lookup = _material_lookup(panel.get("cmap_values"))
    import matplotlib.colors as mcolors
    bg_rgb = mcolors.to_rgb(bg or "#FFFFFF")
    alpha_norm = float(panel.get("fast_alpha_norm", 2.0))   # 每 bin 达到该点数即全亮
    img = np.tile(np.asarray(bg_rgb, dtype=float), (ny * nx, 1)).copy()
    for i, m in enumerate(uniq):
        cnt = cnts[:, i]
        a = np.clip(cnt / alpha_norm, 0.0, 1.0)
        col = np.asarray(mcolors.to_rgb(lookup(m)), dtype=float)
        img = img * (1.0 - a[:, None]) + col * a[:, None]
    rgb = img.reshape(ny, nx, 3)
    ax.imshow(rgb, extent=[x0, x1, y0, y1], origin="lower",
              interpolation="nearest", rasterized=True, zorder=1)
    ax.set_xlabel(panel.get("xlabel", ""))
    ax.set_ylabel(panel.get("ylabel", ""))
    if panel.get("xlim"):
        ax.set_xlim(*panel["xlim"])
    if panel.get("ylim"):
        ax.set_ylim(*panel["ylim"])
    _apply_style(ax, style)
    _apply_aspect(ax, panel)
    # 快速模式仍可叠加（等值线/矢量/追踪点/应变）
    overlay_count = _draw_overlays(ax, panel, style, x, y, idx)
    if panel.get("legend", True) and len(uniq) <= 12:
        import matplotlib.patches as mpatches
        handles = [mpatches.Patch(color=lookup(m), label=C.MATERIAL_NAMES.get(int(m), f"mat {m}"))
                   for m in sorted(uniq)]
        ax.legend(handles=handles, fontsize=style.get("legend_size", 6.5),
                  frameon=False, markerscale=4, ncol=panel.get("legend_ncol", 1),
                  **_legend_kw(panel))
    return {"kind": "material", "n": len(mat), "shown": len(mat), "fast": True,
            "overlays": overlay_count}


def draw_field(ax, panel: dict, style: dict) -> dict:
    """mesh 节点场图（pcolormesh/contour + colorbar）。"""
    fn = panel["file"]
    data = _read(fn, panel.get("dataset", "data"))
    if data.ndim == 1:
        data = data[:, None]
    col = min(int(panel.get("column", 0)), data.shape[1] - 1)
    vals = data[:, col]
    if vals.size == 0:
        raise ValueError("空数据集")
    mesh_file = panel.get("mesh_file") or _guess_mesh_file(fn)
    geo = None
    if mesh_file and Path(mesh_file).exists():
        verts, geo = _mesh_geometry(mesh_file)
        X, Y, _ = _field_grid(verts, geo)
        if X.shape == vals.shape:
            Z = vals.reshape(X.shape)
        elif vals.size == (X.shape[0] - 1) * (X.shape[1] - 1):
            # 单元中心数据（如 projStressTensor）：从节点网格算单元中心
            Xc = 0.5 * (X[:-1, :-1] + X[1:, 1:])
            Yc = 0.5 * (Y[:-1, :-1] + Y[1:, 1:])
            X, Y, Z = Xc, Yc, vals.reshape(Xc.shape)
        else:
            Z = vals.reshape(Y.shape)
    else:
        # 无 mesh 元数据：假设竖直方向长宽已知（nx, ny 从 shape 推断方形近似）
        n = vals.size
        nx = int(round(np.sqrt(n * (1 / 1))))
        ny = n // nx
        while nx * ny < n:
            nx += 1
            ny = n // nx
        Z = vals[: nx * ny].reshape(ny, nx)
        X = np.arange(nx + 1) + 0.5 - 0.5
        Y = np.arange(ny + 1) + 0.5 - 0.5
    # 显示范围筛选（类比物质场阈值提取）：区间外的值 → NaN（pcolormesh 留空）
    mr = panel.get("mask_range") or []
    if len(mr) == 2:
        lo, hi = sorted((float(mr[0]), float(mr[1])))
        Z = np.where((Z >= lo) & (Z <= hi), Z, np.nan)
    cmap = _resolve_cmap(panel)
    pc = ax.pcolormesh(X, Y, Z, cmap=cmap, shading="auto",
                       vmin=panel.get("vmin"), vmax=panel.get("vmax"),
                       rasterized=True)
    if panel.get("contour"):
        lv = panel.get("contour_levels") or 8
        if isinstance(lv, list) and len(lv) == 1:
            lv = int(lv[0]) if float(lv[0]).is_integer() and lv[0] > 1 else lv
        cs = ax.contour(X, Y, Z, levels=lv, colors=panel.get("contour_color", "#333333"),
                        linewidths=0.5)
        if panel.get("clabel", True):
            ax.clabel(cs, inline=True, fontsize=style.get("tick_size", 7) - 1)
    ax.set_xlabel(panel.get("xlabel", ""))
    ax.set_ylabel(panel.get("ylabel", ""))
    if panel.get("xlim"):
        ax.set_xlim(*panel["xlim"])
    if panel.get("ylim"):
        ax.set_ylim(*panel["ylim"])
    cb = None
    if panel.get("colorbar", True):
        cb = ax.figure.colorbar(pc, ax=ax, **(_colorbar_kw(panel) or dict(fraction=0.046, pad=0.04)))
        cb.ax.tick_params(labelsize=style.get("tick_size", 7))
        if panel.get("cbar_label"):
            cb.set_label(panel["cbar_label"], fontsize=style.get("axes_label_size", 8))
    _apply_axes_common(ax, panel)
    _apply_style(ax, style)
    _apply_aspect(ax, panel)
    return {
        "kind": "field", "cmap": panel.get("cmap", "turbo"),
        "cbar": (cb is not None), "unit": panel.get("cbar_label", ""),
    }


def draw_swarm(ax, panel: dict, style: dict) -> dict:
    """粒子散点：color_by 材料（categorical）或数值列（cmap）。"""
    fn = panel["file"]
    with h5py.File(fn, "r") as f:
        xy = f[panel.get("dataset", "data")][:]
    xy = np.asarray(xy, dtype=float)
    if xy.ndim == 1:
        xy = xy[:, None]
    if panel.get("x_col", 0) >= xy.shape[1] or panel.get("y_col", 1) >= xy.shape[1]:
        raise ValueError("坐标列超出 dataset 列数")
    x = xy[:, int(panel.get("x_col", 0))]
    y = xy[:, int(panel.get("y_col", 1))]
    n = len(x)
    if n == 0:
        raise ValueError("空粒子集")

    color_by = panel.get("color_by", "material")
    mat = None
    if color_by == "material":
        mfile = panel.get("material_file") or _sibling(panel.get("file"), "material")
        if mfile and Path(mfile).exists():
            with h5py.File(mfile, "r") as f:
                mat = f[panel.get("material_dataset", "data")][:, 0].astype(int)
        else:
            mat = np.ones(n, dtype=int)
    elif color_by in ("column", "value"):
        ccol = int(panel.get("color_column", 2))
        if ccol >= xy.shape[1]:
            raise ValueError("数值着色列超出")
        mat = None
        cvals = xy[:, ccol]

    # 抽稀：subset_frac 显式指定保留比例（0,1]，优先于采样上限；未指定时按上限自动抽稀
    sf = panel.get("subset_frac")
    if sf:
        frac = min(1.0, max(float(sf), 1.0 / max(n, 1)))
    else:
        cap = int(panel.get("max_points") or MAX_SWARM_POINTS)
        frac = min(1.0, cap / max(n, 1))
    if frac < 1.0:
        rng = np.random.default_rng(7)
        idx = rng.choice(n, int(round(n * frac)), replace=False)
        x, y = x[idx], y[idx]
        if mat is not None:
            mat = mat[idx]
        if color_by == "column":
            cvals = cvals[idx]

    if mat is not None:
        # 按材料 id 查色（与物质场一致：index=id-1，不用 % 取模）
        lookup = _material_lookup(panel.get("cmap_values"))
        colors = np.array([lookup(m) for m in mat])
        uniq = np.unique(mat)
        labels = {u: C.MATERIAL_NAMES.get(int(u), f"mat {u}") for u in uniq}
        import matplotlib.patches as mpatches
        handles = []
        for u in sorted(uniq):
            handles.append(mpatches.Patch(color=lookup(u), label=labels[u]))
        scatter = ax.scatter(x, y, s=float(panel.get("marker_size", 1)),
                             c=colors, rasterized=True,
                             marker=panel.get("marker", "o"), alpha=float(panel.get("alpha", 1.0)),
                             antialiased=False)
        if panel.get("legend", True) and len(handles) <= 20:
            ax.legend(handles=handles, fontsize=style.get("legend_size", 6.5),
                      frameon=False, markerscale=4, **_legend_kw(panel))
    else:
        norm = None
        if panel.get("vmin") is not None or panel.get("vmax") is not None:
            vmin = float(panel.get("vmin", cvals.min()))
            vmax = float(panel.get("vmax", cvals.max()))
            norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
        scatter = ax.scatter(x, y, s=float(panel.get("marker_size", 1)),
                             c=cvals, cmap=_resolve_cmap(panel),
                             norm=norm, rasterized=True, marker=panel.get("marker", "o"),
                             alpha=float(panel.get("alpha", 1.0)),
                             antialiased=False)
        cb = ax.figure.colorbar(scatter, ax=ax, **(_colorbar_kw(panel) or dict(fraction=0.046, pad=0.04)))
        cb.ax.tick_params(labelsize=style.get("tick_size", 7))
    ax.set_xlabel(panel.get("xlabel", ""))
    ax.set_ylabel(panel.get("ylabel", ""))
    if panel.get("xlim"):
        ax.set_xlim(*panel["xlim"])
    if panel.get("ylim"):
        ax.set_ylim(*panel["ylim"])
    _apply_axes_common(ax, panel)
    _apply_style(ax, style)
    _apply_aspect(ax, panel)
    return {"kind": "swarm", "n": n, "shown": len(x)}


def _extract_surface(xy: np.ndarray, mat: np.ndarray, mat_id: int,
                     mode: str, n_seg: int, x_min: float, x_max: float) -> tuple:
    """分段极值提取材料界面线（用户 TopoField/Moho 脚本同款算法）。

    mode='min' → 每段最小 y（如地形 = 空气底）；'max' → 每段最大 y（如莫霍面 = 地幔顶）。
    """
    mask = mat == int(mat_id)
    pts = xy[mask]
    if x_min is not None and x_max is not None:
        pts = pts[(pts[:, 0] >= x_min) & (pts[:, 0] < x_max)]
    if len(pts) == 0:
        return np.array([]), np.array([])
    edges = np.linspace(x_min, x_max, int(n_seg) + 1)
    bin_idx = np.clip(np.digitize(pts[:, 0], edges) - 1, 0, int(n_seg) - 1)
    xs, ys = [], []
    for k in range(int(n_seg)):
        seg = pts[bin_idx == k]
        if seg.size == 0:
            continue
        xs.append(0.5 * (edges[k] + edges[k + 1]))
        ys.append(seg[:, 1].min() if mode == "min" else seg[:, 1].max())
    return np.array(xs), np.array(ys)


def draw_surfaces(ax, panel: dict, style: dict) -> dict:
    """物质场顶/底面提取面板：任选材料 index，三种模式。

    每条 line：{mat, mode, label, color, lw/ls 或 size/alpha}
      mode='max' -> 顶面：按列(分段)取该材料散点每列最高点连成线（如 Moho=地幔顶）
      mode='min' -> 底面：按列取每列最低点连成线（如 地形=空气底、沉积底面）
      mode='all' -> 散点：该材料整个范围的粒子分布（不做极值提取）
    列分辨率 = n_segments（分段数）；提取 x 范围 = x_min/x_max（缺省为全域）。
    """
    fn = panel["file"]
    mfile = panel.get("material_file") or fn
    xy, mat, _ = _subsample_with_cache(fn, mfile if mfile and Path(mfile).exists() else None)
    if mat is None:
        mat = np.ones(len(xy), dtype=int)
    n_seg = int(panel.get("n_segments", 100))
    x_min, x_max = panel.get("x_min"), panel.get("x_max")
    if x_min is None or x_max is None:
        x_min, x_max = float(xy[:, 0].min()), float(xy[:, 0].max())
    default_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    lines = panel.get("lines") or [
        {"mat": 1, "mode": "min", "label": "Topography"},
        {"mat": 2, "mode": "min", "label": "Sed base"},
        {"mat": 3, "mode": "max", "label": "Moho"},
    ]
    drawn = 0
    for i, lc in enumerate(lines):
        mode = str(lc.get("mode", "min"))
        color = lc.get("color", default_colors[i % len(default_colors)])
        label = lc.get("label", f"mat {lc.get('mat')}")
        if mode == "all":
            # 整个范围散点分布：该材料全部（下采样后的）粒子
            pts = xy[mat == int(lc.get("mat", 1))]
            pts = pts[(pts[:, 0] >= x_min) & (pts[:, 0] <= x_max)]
            if len(pts) == 0:
                continue
            ax.scatter(pts[:, 0], pts[:, 1], s=float(lc.get("size", 1)),
                       c=color, alpha=float(lc.get("alpha", 0.8)),
                       rasterized=True, edgecolors="none",
                       antialiased=False, label=label)
            drawn += 1
            continue
        xs, ys = _extract_surface(xy, mat, lc.get("mat", 1), mode,
                                  n_seg, x_min, x_max)
        if len(xs) == 0:
            continue
        ax.plot(xs, ys, color=color,
                lw=float(lc.get("lw", style.get("line_width", 1.2))),
                ls=lc.get("ls", "-"), label=label)
        drawn += 1
    if panel.get("legend", True) and drawn:
        ax.legend(fontsize=style.get("legend_size", 6.5), frameon=False,
                  handlelength=1.8, **_legend_kw(panel))
    ax.set_xlabel(panel.get("xlabel", "x [km]"))
    ax.set_ylabel(panel.get("ylabel", "y [km]"))
    if panel.get("xlim"):
        ax.set_xlim(*panel["xlim"])
    if panel.get("ylim"):
        ax.set_ylim(*panel["ylim"])
    _apply_axes_common(ax, panel)
    _apply_style(ax, style)
    _apply_aspect(ax, panel)
    return {"kind": "surfaces", "lines": drawn}


def draw_curve(ax, panel: dict, style: dict) -> dict:
    """1D 曲线：dataset 单列或多列；支持第二轴。"""
    fn = panel["file"]
    with h5py.File(fn, "r") as f:
        ds = f[panel.get("dataset", "data")]
        n = ds.shape[0]
        if n > STATS_SAMPLE:
            # 分段块读，避免随机索引拖慢
            seg = STATS_SAMPLE // 3
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
    x = None
    if panel.get("x_column") is not None:
        x = arr[:, int(panel["x_column"])]
    elif panel.get("x_values") is not None:
        x = np.asarray(panel["x_values"], dtype=float)[: arr.shape[0]]
    else:
        x = np.arange(arr.shape[0])
    style2 = None
    if panel.get("style_conf"):
        style2 = panel["style_conf"]
    else:
        style2 = {"colors": ["#2878B5", "#D97924", "#2CA02C", "#D7191C", "#444444"],
                  "lw": style.get("line_width", style.get("axes_linewidth", 0.75))}
    colors = style2.get("colors", ["#2878B5", "#D97924"])
    lw_panel = panel.get("line_width")
    ls_panel = panel.get("line_style")
    mk_panel = panel.get("marker")
    ms_panel = panel.get("marker_size")
    sel_cols = panel.get("columns") or list(range(arr.shape[1]))
    for i, cnum in enumerate(sel_cols):
        ax.plot(x, arr[:, int(cnum)], color=colors[i % len(colors)],
                lw=lw_panel if lw_panel is not None else style2.get("lw", 1.2),
                ls=ls_panel if ls_panel else (style2.get("linestyles", [None, (0, (4, 2))])[i % 2] or None),
                marker=mk_panel if mk_panel else None,
                markersize=float(ms_panel) if ms_panel else None,
                label=panel.get("column_names")[i] if panel.get("column_names") and i < len(panel["column_names"]) else f"col {cnum}")
    if panel.get("xlim"):
        ax.set_xlim(*panel["xlim"])
    if panel.get("ylim"):
        ax.set_ylim(*panel["ylim"])
    if panel.get("hlines"):
        for hv in panel["hlines"]:
            ax.axhline(hv.get("y", 0), color=hv.get("color", "#444444"),
                       ls=hv.get("ls", (0, (5, 3))), lw=hv.get("lw", 1.0))
            if hv.get("text"):
                ax.text(hv.get("x", 0.01), hv.get("y", 0), hv["text"],
                        transform=ax.get_xaxis_transform(), fontsize=style.get("tick_size", 7) - 0.5,
                        color=hv.get("color", "#444444"), va="top")
    if panel.get("legend", True):
        ax.legend(fontsize=style.get("legend_size", 6.5), frameon=False,
                  handlelength=1.8, **_legend_kw(panel))
    ax.set_xlabel(panel.get("xlabel", ""))
    ax.set_ylabel(panel.get("ylabel", ""))
    _apply_axes_common(ax, panel)
    _apply_style(ax, style)
    return {"kind": "curve", "ncols": len(sel_cols)}


def draw_material(ax, panel: dict, style: dict) -> dict:
    """物质场面板：swarm 坐标 + materialField 离散着色。

    自动与用户习惯对齐：
    - 默认 Qaidam 配色（config.QAIDAM_MATERIAL_COLORS）；可用 `cmap_values` 覆盖
    - 支持深色背景 `bg_color`（用户常用 #404040）
    - 叠加层 overlays：
        contour  -> 温度等值线（mesh 场，可固定 levels）
        scatter  -> 应变等粒子场（阈值筛选后散点着色，如 plasticStrain >= 1.5 & y < 4）
        field    -> 半透明 pcolormesh 叠加（mesh 场，如粘度）
    """
    fn = panel["file"]
    if panel.get("fast"):
        return _draw_material_fast(ax, panel, style)
    mfile = panel.get("material_file") or fn
    max_pts = int(panel.get("max_points") or MAX_SWARM_POINTS)
    sf = panel.get("subset_frac")
    if sf:
        # subset_frac 显式指定保留比例，与采样上限取较小者
        with h5py.File(fn, "r") as f:
            n_total = f["data"].shape[0]
        max_pts = min(max_pts, max(1, round(n_total * min(1.0, float(sf)))))
    xy, mat, idx = _subsample_with_cache(fn, mfile if mfile and Path(mfile).exists() else None,
                                         max_pts=max_pts)
    x, y = xy[:, int(panel.get("x_col", 0))], xy[:, int(panel.get("y_col", 1))]
    n = len(x)
    if n == 0:
        raise ValueError("空粒子集")
    if mat is None:
        mat = np.ones(n, dtype=int)

    # 材料过滤（只画选定材料，用户用于只看盆地/造山带）
    only_mats = panel.get("only_materials")
    if only_mats:
        keep = np.isin(mat, [int(v) for v in only_mats])
        x, y, mat = x[keep], y[keep], mat[keep]
        if idx is not None:
            idx = idx[keep]

    # 深色背景
    bg = panel.get("bg_color")
    if bg:
        ax.set_facecolor(bg)

    # 材料配色：cmap_values 优先，否则 Qaidam 预设（按材料 id 查色，不用 % 取模）
    cmap_values = panel.get("cmap_values") or list(C.QAIDAM_MATERIAL_COLORS.values())
    lookup = _material_lookup(cmap_values)
    raster = bool(panel.get("rasterized", True))
    colors = np.array([lookup(m) for m in mat])
    _ms = float(panel.get("marker_size", 1))
    ax.scatter(x, y, s=_ms,
               c=colors, rasterized=raster, marker=panel.get("marker", "o"),
               alpha=float(panel.get("alpha", 1.0)),
               edgecolors=panel.get("edgecolors", "none"),
               linewidths=float(panel.get("edge_width", 0.4)),
               antialiased=_ms < 1)  # 亚像素 marker 开抗锯齿，避免黑噪点
    if panel.get("legend", True):
        uniq = np.unique(mat)
        labels = {u: C.MATERIAL_NAMES.get(int(u), f"mat {u}") for u in uniq}
        import matplotlib.patches as mpatches
        handles = [mpatches.Patch(color=lookup(u), label=labels[u])
                   for u in sorted(uniq)]
        _ncol = panel.get("legend_ncol")
        if not _ncol and panel.get("legend_loc") == "outside bottom":
            _ncol = 3   # 图外底部：横向 3 列更紧凑
        ax.legend(handles=handles, fontsize=style.get("legend_size", 6.5),
                  frameon=False, markerscale=4, ncol=_ncol or 1,
                  **_legend_kw(panel))

    # ---- 叠加层（与快速模式共用） ----
    overlay_count = _draw_overlays(ax, panel, style, x, y, idx)

    ax.set_xlabel(panel.get("xlabel", ""))
    ax.set_ylabel(panel.get("ylabel", ""))
    if panel.get("xlim"):
        ax.set_xlim(*panel["xlim"])
    if panel.get("ylim"):
        ax.set_ylim(*panel["ylim"])
    _apply_axes_common(ax, panel)
    _apply_style(ax, style)
    _apply_aspect(ax, panel)
    return {"kind": "material", "n": n, "shown": len(x),
            "overlays": overlay_count}


def _draw_overlays(ax, panel: dict, style: dict, x, y, idx) -> dict:
    """物质场叠加层循环（contour/scatter/field/vectors/tracers）。"""
    overlay_count = {"contour": 0, "scatter": 0, "field": 0, "vectors": 0, "tracers": 0}
    fn = panel["file"]
    for ov in panel.get("overlays") or []:
        otype = ov.get("type", "contour")
        if otype not in overlay_count:
            otype = "field"
        ocount = overlay_count[otype] + 1
        overlay_count[otype] = ocount
        ofile = ov.get("file") or fn
        if not ofile or not Path(ofile).exists():
            continue
        try:
            if otype == "contour":
                _overlay_contour(ax, ov, ofile, style)
            elif otype == "scatter":
                _overlay_scatter(ax, ov, ofile, style, x, y, idx)
            elif otype == "field":
                _overlay_field(ax, ov, ofile, style)
            elif otype == "vectors":
                _overlay_vectors(ax, ov, ofile, style)
            elif otype == "tracers":
                _overlay_tracers(ax, ov, ofile, style)
        except Exception as e:  # noqa: BLE001
            ax.text(0.5, 0.02, f"overlay{ocount}({otype}) failed: {e}",
                    transform=ax.transAxes, ha="center", va="bottom",
                    fontsize=6, color="#B22222")
    return overlay_count


def _overlay_contour(ax, ov: dict, ofile: str, style: dict) -> None:
    """温度等值线叠加（mesh 节点场，默认 473/673/873/1073/1273/1473 K）。"""
    with h5py.File(ofile, "r") as f:
        vals = f[ov.get("dataset", "data")][:].astype(float).reshape(-1)
    mesh_file = ov.get("mesh_file") or _guess_mesh_file(ofile)
    if not mesh_file or not Path(mesh_file).exists():
        raise ValueError("缺少 mesh.h5")
    verts, geo = _mesh_geometry(mesh_file)
    X, Y, _ = _field_grid(verts, geo)
    if vals.size != X.size:
        if vals.size == (X.shape[0] - 1) * (X.shape[1] - 1):
            # 单元中心数据（如 projStressTensor）：节点网格 → 单元中心网格
            X = 0.5 * (X[:-1, :-1] + X[1:, 1:])
            Y = 0.5 * (Y[:-1, :-1] + Y[1:, 1:])
        else:
            raise ValueError(f"{ofile} 节点数 {vals.size} 与网格 {X.size} 不匹配")
    Z = vals.reshape(X.shape)
    levels = ov.get("levels") or [473, 673, 873, 1073, 1273, 1473]
    color = ov.get("color", "#ff557f")
    cs = ax.contour(X, Y, Z, levels=levels, colors=color,
                    linewidths=float(ov.get("linewidth", 0.8)),
                    linestyles=ov.get("linestyle", "--"))
    if ov.get("clabel", True):
        mr = ov.get("label_region") or {}
        if mr:
            manual = []
            for _i, segs in enumerate(cs.allsegs):
                vis = [(float(v[0]), float(v[1])) for s in segs for v in s
                       if mr.get("x0", -1e9) <= v[0] <= mr.get("x1", 1e9)
                       and mr.get("y0", -1e9) <= v[1] <= mr.get("y1", 1e9)]
                if vis:
                    mid_y = np.mean([q[1] for q in vis])
                    manual.append(min(vis, key=lambda q: abs(q[1] - mid_y)))
            ax.clabel(cs, inline=True, fmt=lambda t: f"{int(t - 273)}",
                      manual=manual or None, fontsize=style.get("tick_size", 7) - 1)
        else:
            try:
                ax.clabel(cs, inline=True, fmt=lambda t: f"{int(t - 273)}",
                          fontsize=style.get("tick_size", 7) - 1)
            except Exception:  # noqa: BLE001
                pass


def _overlay_scatter(ax, ov: dict, ofile: str, style: dict, sx, sy,
                     idx: np.ndarray | None = None) -> None:
    """应变等粒子场叠加：阈值筛选后散点着色。

    阈值写法（与用户脚本一致）：
      mask_value: {ge: 1.5}            -> 筛选该场值 >= 1.5
      mask_y:     {lt: 4}              -> 粒子 y < 4
      mask_material: [4, 7]            -> 只叠加指定材料

    idx：材质面板下采样时对粒子坐标的索引；传入后按同一索引读取
    粒子场值，保证“坐标-值”一一对应（否则 20 万采样点与 580 万
    粒子场前段错位，会出现杂点）。
    """
    with h5py.File(ofile, "r") as f:
        vals = f[ov.get("dataset", "data")][:]
    vals = np.asarray(vals, dtype=float).reshape(-1)
    if idx is not None:
        vals = vals[idx]
    n = min(len(sx), len(vals))
    vx, vy, vv = sx[:n], sy[:n], vals[:n]
    mask = np.ones(n, dtype=bool)
    mv = ov.get("mask_value") or {}
    for op, thr in mv.items():
        if op == "ge": mask &= vv >= float(thr)
        elif op == "le": mask &= vv <= float(thr)
        elif op == "gt": mask &= vv > float(thr)
        elif op == "lt": mask &= vv < float(thr)
    my = ov.get("mask_y") or {}
    for op, thr in my.items():
        if op == "ge": mask &= vy >= float(thr)
        elif op == "le": mask &= vy <= float(thr)
        elif op == "gt": mask &= vy > float(thr)
        elif op == "lt": mask &= vy < float(thr)
    if mask.any():
        sc = ax.scatter(vx[mask], vy[mask], c=vv[mask],
                        cmap=_resolve_cmap(ov, default="hot_r"), s=float(ov.get("size", 1)),
                        alpha=float(ov.get("alpha", 0.9)),
                        vmin=float(ov["vmin"]) if ov.get("vmin") is not None else None,
                        vmax=float(ov["vmax"]) if ov.get("vmax") is not None else None,
                        edgecolors="none", rasterized=True, antialiased=False)
        if ov.get("colorbar", False):
            cb = ax.figure.colorbar(sc, ax=ax, **(_colorbar_kw(ov) or dict(fraction=0.046, pad=0.04)))
            cb.ax.tick_params(labelsize=style.get("tick_size", 7))
            if ov.get("cbar_label"):
                cb.set_label(ov["cbar_label"], fontsize=style.get("axes_label_size", 8))


def _overlay_field(ax, ov: dict, ofile: str, style: dict) -> None:
    """半透明 pcolormesh 叠加（如粘度场 log10）。"""
    with h5py.File(ofile, "r") as f:
        vals = f[ov.get("dataset", "data")][:]
    vals = np.asarray(vals, dtype=float)
    if vals.ndim == 2:
        vals = vals[:, int(ov.get("column", 0))] if ov.get("column") is not None else vals[:, 0]
    vals = vals.reshape(-1)
    mesh_file = ov.get("mesh_file") or _guess_mesh_file(ofile)
    if not mesh_file or not Path(mesh_file).exists():
        raise ValueError("缺少 mesh.h5")
    verts, geo = _mesh_geometry(mesh_file)
    X, Y, _ = _field_grid(verts, geo)
    if vals.size == X.size:
        Z = vals.reshape(X.shape)
    else:
        raise ValueError("叠加场节点数与网格不匹配")
    # 显示范围筛选（按原始物理量区间；log10 前生效）：区间外 → NaN 留空
    mr = ov.get("mask_range") or []
    if len(mr) == 2:
        lo, hi = sorted((float(mr[0]), float(mr[1])))
        Z = np.where((Z >= lo) & (Z <= hi), Z, np.nan)
    vmin, vmax = ov.get("vmin"), ov.get("vmax")
    if ov.get("log10"):
        Z = np.log10(np.clip(Z, 1e-30, None))
        if vmin is not None:
            vmin = float(np.log10(float(vmin)))
        if vmax is not None:
            vmax = float(np.log10(float(vmax)))
    pc = ax.pcolormesh(X, Y, Z, cmap=_resolve_cmap(ov, default="viridis"),
                       alpha=float(ov.get("alpha", 0.5)),
                       vmin=vmin, vmax=vmax, shading="auto", rasterized=True)
    if ov.get("colorbar", False):
        cb = ax.figure.colorbar(pc, ax=ax, **(_colorbar_kw(ov) or dict(fraction=0.046, pad=0.04)))
        cb.ax.tick_params(labelsize=style.get("tick_size", 7))
        if ov.get("cbar_label"):
            cb.set_label(ov["cbar_label"], fontsize=style.get("axes_label_size", 8))


def _guess_mesh_file(fn: str) -> str | None:
    d = Path(fn).parent
    if Path(d / "mesh.h5").exists():
        return str(d / "mesh.h5")
    if Path(d / "Mesh.h5").exists():
        return str(d / "Mesh.h5")
    return None


def _sibling(fn: str, prefix: str) -> str | None:
    d = Path(fn).parent
    name = Path(fn).name
    import re
    m = re.search(r"(.*?)-(\d+)", name)
    base = m.group(1) if m else Path(name).stem
    for cand in d.glob(f"{prefix}*.h5"):
        if base in cand.name or cand.name.startswith(prefix):
            return str(cand)
    return None


# --------------------------------------------------------------------------
# 主渲染
# --------------------------------------------------------------------------


def draw_stress(ax, panel: dict, style: dict) -> dict:
    """Stress field on element centers (projStressTensor + mesh en_map).

    column: 0=sxx, 1=syy, 2=sxy. Diverging cmap (RdBu_r) + symmetric vmin/vmax by default.
    """
    fn = panel["file"]
    mesh_file = panel.get("mesh_file") or _guess_mesh_file(fn)
    if not mesh_file or not Path(mesh_file).exists():
        raise ValueError("mesh.h5 required for element centers")
    with h5py.File(fn, "r") as f:
        data = f[panel.get("dataset", "data")][:].astype(float)
    with h5py.File(mesh_file, "r") as f:
        verts = f["vertices"][:]
        en = f["en_map"][:].astype(np.int64)
    centers = verts[en].mean(axis=1)
    col = min(int(panel.get("column", 1)), data.shape[1] - 1)
    vals = data[:, col]
    # 显示范围筛选：只保留区间内的单元（区间外不绘制）
    mr = panel.get("mask_range") or []
    if len(mr) == 2:
        lo, hi = sorted((float(mr[0]), float(mr[1])))
        keep = (vals >= lo) & (vals <= hi)
        vals, centers = vals[keep], centers[keep]
    vmin = panel.get("vmin")
    vmax = panel.get("vmax")
    if vmin is None and vmax is None:
        v = float(np.nanpercentile(np.abs(vals), 95)) or 1.0
        vmin, vmax = -v, v
    sc = ax.scatter(centers[:, 0], centers[:, 1], c=vals,
                    cmap=_resolve_cmap(panel, default="RdBu_r"),
                    vmin=vmin, vmax=vmax, s=float(panel.get("marker_size", 1.5)),
                    rasterized=True, antialiased=False)
    # 默认锁定模型全域范围（不留 autoscale 边距，左右不空）
    if not panel.get("xlim") and len(vals):
        ax.set_xlim(float(centers[:, 0].min()), float(centers[:, 0].max()))
    if not panel.get("ylim") and len(vals):
        ax.set_ylim(float(centers[:, 1].min()), float(centers[:, 1].max()))
    if panel.get("colorbar", True):
        cb = ax.figure.colorbar(sc, ax=ax, **(_colorbar_kw(panel) or dict(fraction=0.046, pad=0.04)))
        cb.ax.tick_params(labelsize=style.get("tick_size", 7))
        cb.set_label(panel.get("cbar_label", "Stress [MPa]"),
                     fontsize=style.get("axes_label_size", 8))
    ax.set_xlabel(panel.get("xlabel", "x [km]"))
    ax.set_ylabel(panel.get("ylabel", "y [km]"))
    if panel.get("xlim"):
        ax.set_xlim(*panel["xlim"])
    if panel.get("ylim"):
        ax.set_ylim(*panel["ylim"])
    _apply_axes_common(ax, panel)
    _apply_style(ax, style)
    _apply_aspect(ax, panel)
    return {"kind": "stress", "n": len(vals)}

DRAWS = {"field": draw_field, "swarm": draw_swarm, "curve": draw_curve,
         "material": draw_material, "surfaces": draw_surfaces,
         "stress": draw_stress}


def _parse_template(tpl: object) -> list | None:
    """'2+1' / '2x2' → [2,1] / [2,2]（每行格数）；非法返回 None。"""
    if not tpl:
        return None
    parts = [p for p in str(tpl).lower().replace("x", "+").split("+") if p.strip()]
    try:
        rows_spec = [int(p) for p in parts]
    except ValueError:
        return None
    if not rows_spec or any(r <= 0 for r in rows_spec):
        return None
    return rows_spec


def _auto_template(n: int) -> list:
    """面板数 → 默认模板（论文常见版式）；空列表 = 回退规则网格。"""
    return {1: [1], 2: [1, 1], 3: [2, 1], 4: [2, 2], 5: [3, 2], 6: [3, 3]}.get(n, [])


def _layout(orientation: str, npanels: int, layout: dict | None = None):
    """A4 画板布局：返回 (rows, cols, figsize, hr, wr, cells, capacity)。

    cells = [(row, col_start, col_span)] 按面板顺序的网格切片（ultraplot 式模板）；
    模板语法 '2+1'/'4+1'/'2x2'：每行格数，行内等宽，格数少的行自动通栏合并；
    cols = 各行格数的最小公倍数。未指定模板且未手动设 rows/cols 时按面板数自动选。
    layout 另支持 height_ratios（行高比，如 '3,1'）。
    """
    figsize = (11.69, 8.27) if orientation == "landscape" else (8.27, 11.69)
    layout = layout or {}
    try:
        m_rows = int(layout.get("rows") or 0)
        m_cols = int(layout.get("cols") or 0)
    except (TypeError, ValueError):
        m_rows = m_cols = 0
    spec = _parse_template(layout.get("template"))
    if spec is None and (m_rows <= 0 or m_cols <= 0):
        spec = _auto_template(npanels) or None
    if spec is not None:
        from math import gcd
        cols = 1
        for c in spec:
            cols = cols * c // gcd(cols, c)
        cells = []
        for r, cnt in enumerate(spec):
            span = cols // cnt
            for k in range(cnt):
                cells.append((r, k * span, span))
        hr = _ratios(layout.get("height_ratios"), len(spec))
        return len(spec), cols, figsize, hr, [1.0] * cols, cells, len(cells)
    rows, cols = m_rows, m_cols
    if rows <= 0 or cols <= 0:
        if npanels <= 1:
            rows = cols = 1
        elif npanels == 2:
            rows, cols = 2, 1
        elif npanels <= 4:
            rows = cols = 2
        else:
            rows, cols = int(np.ceil(npanels / 2)), 2
    hr = _ratios(layout.get("height_ratios"), rows)
    wr = _ratios(layout.get("width_ratios"), cols)
    cells = [(i // cols, i % cols, 1) for i in range(rows * cols)]
    return rows, cols, figsize, hr, wr, cells, rows * cols


def _ratios(v: object, n: int) -> list:
    if isinstance(v, str):
        try:
            v = [float(x) for x in v.split(",") if x.strip()]
        except ValueError:
            v = None
    if not isinstance(v, (list, tuple)) or not v:
        return [1.0] * n
    out = [float(x) for x in v[:n]]
    while len(out) < n:
        out.append(out[-1] if out else 1.0)
    return out


def _spec_cache_key(req: dict) -> str:
    """渲染 spec + 相关文件 mtime + 代码版本的指纹；相同请求直接复用产物（秒回）。"""
    import hashlib
    import sys
    h = hashlib.sha1()
    # 代码版本指纹：plotters/config 源码改动后旧缓存自动失效
    for mod in ("core.plotters", "core.config"):
        try:
            mf = Path(sys.modules[mod].__file__)
            h.update(f"{mf}:{os.path.getmtime(mf)}".encode())
        except Exception:  # noqa: BLE001
            pass
    h.update(json.dumps(req, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    for p in req.get("panels") or []:
        for k in ("file", "material_file", "mesh_file"):
            f = p.get(k)
            if f and Path(f).exists():
                h.update(f"{f}:{os.path.getsize(f)}:{os.path.getmtime(f)}".encode())
        for ov in p.get("overlays") or []:
            for f in [ov.get("file")] + list(ov.get("files") or []):
                if f and Path(f).exists():
                    h.update(f"{f}:{os.path.getsize(f)}:{os.path.getmtime(f)}".encode())
    return h.hexdigest()[:20]


def render_plot(req: dict) -> dict:
    """渲染一个绘图请求，返回 plot_id 与面板元信息。"""
    plot_id = secrets.token_hex(6)
    panels = req.get("panels") or []
    if not panels:
        raise ValueError("没有面板")

    # 结果缓存：同 spec（含文件 mtime）直接复用预览 PNG
    key = _spec_cache_key(req)
    if key:
        cached_png = PLOT_DIR / f"_cached_{key}.png"
        cached_json = PLOT_DIR / f"_cached_{key}.json"
        if cached_png.exists() and cached_json.exists():
            try:
                shutil.copy2(cached_png, PLOT_DIR / f"{plot_id}.png")
                meta = json.loads(cached_json.read_text("utf-8"))
                meta["plot_id"] = plot_id
                meta["spec"] = req
                meta["files"] = {
                    "png": f"/api/plots/{plot_id}.png",
                    "png300": f"/api/plots/{plot_id}.png300.png",
                    "svg": f"/api/plots/{plot_id}.svg",
                    "pdf": f"/api/plots/{plot_id}.pdf",
                }
                (PLOT_DIR / f"{plot_id}.json").write_text(
                    json.dumps(meta, ensure_ascii=False), "utf-8")
                return meta
            except Exception:  # noqa: BLE001
                pass

    orientation = req.get("orientation", "portrait")
    style = dict(C.JOURNAL_STYLE)
    style.update(req.get("style") or {})
    rows, cols, figsize, hr, wr, cells, capacity = _layout(
        orientation, len(panels), req.get("layout"))

    plt.rcParams.update({
        "font.family": style.get("font_family", "Arial"),
        "font.size": style.get("font_size", 7),
        "axes.linewidth": style.get("axes_linewidth", 0.75),
        "svg.fonttype": style.get("svg_fonttype", "none"),
        "axes.unicode_minus": False,
    })
    fig = plt.figure(figsize=figsize)
    fig.dpi = 100
    gs = fig.add_gridspec(rows, cols,
                          hspace=style.get("panel_gap", 0.55),
                          wspace=0.35,
                          height_ratios=hr, width_ratios=wr)
    panel_meta = []
    dropped = max(0, len(panels) - capacity)
    for i, panel in enumerate(panels[:capacity]):
        # 模板放置：cells 由 _layout 按 '2+1' 等模板算出 (row, col_start, span)
        r_, c0, span = cells[i]
        ax = fig.add_subplot(gs[r_, c0:c0 + span])
        cell = gs[r_, c0:c0 + span].get_position(fig)
        if panel.get("aspect") in BOX_RATIOS:
            _apply_box_ratio(ax, cell, BOX_RATIOS[panel.get("aspect")])
            cell = ax.get_position()   # 图例/colorbar 避让以适配后的盒为准
        kind = panel.get("kind", "field")
        if kind not in DRAWS:
            ax.text(0.5, 0.5, f"unsupported: {kind}", transform=ax.transAxes,
                    ha="center")
            viewer = {"kind": kind}
        else:
            n_axes_before = len(fig.axes)
            try:
                viewer = DRAWS[kind](ax, panel, style)
                # 记录本面板新增的 colorbar axes（供图例避让使用）
                for _cbax in fig.axes[n_axes_before:]:
                    if _cbax is not ax:
                        ax._h5_cb_ax = _cbax
                if panel.get("legend_loc") == "outside right":
                    _fix_outside_right_legend(fig, ax, cell)
                elif panel.get("legend_loc") == "outside bottom":
                    _fix_outside_bottom_legend(fig, ax, cell)
                if panel.get("title"):
                    ax.set_title(panel["title"], fontsize=style.get("title_size", 8))
                # 面板标注 (a) (b) ...
                if panel.get("label") or req.get("auto_panel_labels", True):
                    lab = panel.get("label") or _panel_label(i)
                    ax.text(0.005, 0.97, lab, transform=ax.transAxes,
                            fontsize=style.get("panel_label_size", 10),
                            fontweight=style.get("panel_label_weight", "bold"),
                            va="top", ha="left",
                            bbox=dict(facecolor="white", alpha=0.85,
                                      edgecolor="none", pad=1.0))
            except Exception as e:  # noqa: BLE001
                ax.text(0.5, 0.5, f"{kind} draw failed:\n{e}", transform=ax.transAxes,
                        ha="center", va="center", fontsize=8, color="#B22222")
                viewer = {"kind": kind, "error": str(e)}

        # 关键：记录 axes 显示 bbox（以输出 dpi 像素）与数据范围（用当前 ax，
        # 避免 colorbar 等其它 axes 混入 fig.axes 导致错位）
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbox = ax.get_window_extent(renderer=renderer)
        k = PREVIEW_DPI / 100.0   # 100dpi 基准 bbox → 预览 dpi 像素（probe 用）
        axes_meta = {
            "i": i, "kind": kind,
            "x0_px": float(bbox.x0) * k, "y0_px": float(bbox.y0) * k,
            "w_px": float(bbox.width) * k, "h_px": float(bbox.height) * k,
        }
        try:
            axes_meta["xlim"] = [float(ax.get_xlim()[0]), float(ax.get_xlim()[1])]
            axes_meta["ylim"] = [float(ax.get_ylim()[0]), float(ax.get_ylim()[1])]
            axes_meta["xscale"] = str(ax.get_xscale())
            axes_meta["yscale"] = str(ax.get_yscale())
        except Exception:  # noqa: BLE001
            pass
        panel_meta.append({**axes_meta, **viewer, "file": panel.get("file", ""),
                           "dataset": panel.get("dataset", ""),
                           "mesh_file": panel.get("mesh_file"),
                           "x_col": panel.get("x_col"),
                           "y_col": panel.get("y_col"),
                           "columns": panel.get("columns"),
                           "x_column": panel.get("x_column"),
                           "material_file": panel.get("material_file"),
                           "only_materials": panel.get("only_materials")})

    # 保存产物：预览 png 用 300dpi（屏幕大图清晰），svg/pdf/png300 导出时按需生成
    base = PLOT_DIR / plot_id
    fig.savefig(base.with_suffix(".png"), dpi=PREVIEW_DPI, facecolor="white")
    plt.close(fig)

    meta = {
        "plot_id": plot_id,
        "figsize_in": figsize,
        "orientation": orientation,
        "dpi": PREVIEW_DPI,
        "layout": {"rows": rows, "cols": cols, "dropped": dropped},
        "panels": panel_meta,
        "files": {
            "png": f"/api/plots/{plot_id}.png",
            "png300": f"/api/plots/{plot_id}.png300.png",
            "svg": f"/api/plots/{plot_id}.svg",
            "pdf": f"/api/plots/{plot_id}.pdf",
        },
        "spec": req,   # 供 ensure_hi_res 按需重渲染高分辨率产物
    }
    (PLOT_DIR / f"{plot_id}.json").write_text(json.dumps(meta, ensure_ascii=False), "utf-8")
    # 写缓存（同 spec 复用）
    if key:
        try:
            shutil.copy2(base.with_suffix(".png"), PLOT_DIR / f"_cached_{key}.png")
            (PLOT_DIR / f"_cached_{key}.json").write_text(
                json.dumps(meta, ensure_ascii=False), "utf-8")
        except OSError:
            pass
    return meta


def ensure_hi_res(plot_id: str) -> bool:
    """按需生成 svg / pdf / png300（首次调用时用保存的 spec 重新渲染，之后缓存）。"""
    base = PLOT_DIR / plot_id
    pdf, png300, svg = (base.with_suffix(".pdf"), base.with_suffix(".png300.png"),
                        base.with_suffix(".svg"))
    if pdf.exists() and png300.exists() and svg.exists():
        return True
    meta = get_meta(plot_id)
    if not meta or not meta.get("spec"):
        return False
    spec = meta["spec"]
    orientation = spec.get("orientation", "portrait")
    style = dict(C.JOURNAL_STYLE)
    style.update(spec.get("style") or {})
    rows, cols, figsize, hr, wr, cells, capacity = _layout(
        orientation, len(spec.get("panels") or []), spec.get("layout"))
    plt.rcParams.update({
        "font.family": style.get("font_family", "Arial"),
        "font.size": style.get("font_size", 7),
        "axes.linewidth": style.get("axes_linewidth", 0.75),
        "svg.fonttype": style.get("svg_fonttype", "none"),
        "axes.unicode_minus": False,
    })
    fig = plt.figure(figsize=figsize)
    fig.dpi = 100
    gs = fig.add_gridspec(rows, cols,
                          hspace=style.get("panel_gap", 0.55), wspace=0.35,
                          height_ratios=hr, width_ratios=wr)
    for i, panel in enumerate((spec.get("panels") or [])[:capacity]):
        r_, c0, span = cells[i]
        ax = fig.add_subplot(gs[r_, c0:c0 + span])
        cell = gs[r_, c0:c0 + span].get_position(fig)
        if panel.get("aspect") in BOX_RATIOS:
            _apply_box_ratio(ax, cell, BOX_RATIOS[panel.get("aspect")])
            cell = ax.get_position()   # 图例/colorbar 避让以适配后的盒为准
        kind = panel.get("kind", "field")
        n_axes_before = len(fig.axes)
        try:
            DRAWS[kind](ax, panel, style)
            for _cbax in fig.axes[n_axes_before:]:
                if _cbax is not ax:
                    ax._h5_cb_ax = _cbax
            if panel.get("legend_loc") == "outside right":
                _fix_outside_right_legend(fig, ax, cell)
            elif panel.get("legend_loc") == "outside bottom":
                _fix_outside_bottom_legend(fig, ax, cell)
            if panel.get("label") or spec.get("auto_panel_labels", True):
                lab = panel.get("label") or _panel_label(i)
                ax.text(0.005, 0.97, lab, transform=ax.transAxes,
                        fontsize=style.get("panel_label_size", 10),
                        fontweight=style.get("panel_label_weight", "bold"),
                        va="top", ha="left",
                        bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1.0))
        except Exception:  # noqa: BLE001
            pass
    fig.savefig(base.with_suffix(".pdf"), dpi=100, facecolor="white")
    fig.savefig(base.with_suffix(".png300.png"), dpi=300, facecolor="white")
    fig.savefig(base.with_suffix(".svg"), dpi=100, facecolor="white")
    plt.close(fig)
    return True


def _panel_label(i: int) -> str:
    return f"({'abcdefghij'[i]})"


def get_meta(plot_id: str) -> dict | None:
    p = PLOT_DIR / f"{plot_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text("utf-8"))