#!/usr/bin/env python3
"""PlotUWG 端到端自检：真实 uw217 / Badlands h5 数据。

用法（geopixel 环境）:
    PLOTUWG_UW_DIR=/path/to/uw217_model_dir \\
    PLOTUWG_BD_DIR=/path/to/badlands/tin.time50.hdf5 \\
    python selftest.py
未设置环境变量时自动跳过全部用例。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# 模型测试数据路径：用环境变量注入（仓库公开，不写死本机路径）
#   PLOTUWG_UW_DIR  = 一个 uw217 模型输出目录（含 swarm-0.h5、materialField-0.h5、mesh.h5 等）
#   PLOTUWG_BD_DIR  = 一个 Badlands 输出文件（如 tin.time50.hdf5）
UW = os.environ.get("PLOTUWG_UW_DIR", "")
BD = os.environ.get("PLOTUWG_BD_DIR", "")
if not UW or not BD:
    print("跳过：设置 PLOTUWG_UW_DIR 与 PLOTUWG_BD_DIR 后运行（见 README「Self-Test」）")
    sys.exit(0)

ok = 0; fail = 0

def check(name, fn):
    global ok, fail
    try:
        fn()
        print(f"  ✓ {name}")
        ok += 1
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        fail += 1

print("== 0. 模型时间步扫描 ==")
from core import h5inspector

def t_stepscan():
    s = h5inspector.scan_model_dir(UW)
    assert s["is_model_dir"]
    assert "materialField" in s["fields"] and "swarm" in s["fields"]
    assert len(s["steps"]) >= 2 and 0 in s["steps"]
check("模型目录时间步扫描（时间自动对齐）", t_stepscan)

print("== 1. 检视器 ==")
from core import h5inspector
def t_inspect_swarm():
    inf = h5inspector.inspect_h5_file(UW + "/swarm-0.h5")
    assert inf["type"] == "swarm" and inf["n_datasets"] == 1
    assert inf["tree"][0]["head"][:2]
check("inspect swarm-0.h5 (512万粒子, 秒开)", t_inspect_swarm)

def t_inspect_mesh():
    inf = h5inspector.inspect_h5_file(UW + "/mesh.h5")
    assert inf["type"] == "mesh"
    assert "vertices" in {n["name"] for n in inf["tree"]}
check("inspect mesh.h5", t_inspect_mesh)

def t_inspect_tin():
    inf = h5inspector.inspect_h5_file(BD)
    assert inf["type"] == "badlands"
check("inspect Badlands tin.time50.hdf5", t_inspect_tin)

def t_listing():
    out = h5inspector.directory_listing(UW)
    assert out["is_dir"] and any(i["is_h5"] for i in out["items"])
check("目录浏览", t_listing)

print("== 2. 渲染 ==")
from core import plotters as P

def t_material():
    # 物质场：材质 + 温度等值线叠加 + 应变散点（阈值）+ 粘度场半透明
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "material",
            "file": UW + "/swarm-0.h5", "dataset": "data",
            "material_file": UW + "/materialField-0.h5",
            "bg_color": "#404040", "marker_size": 1, "legend": True,
            "xlim": [200, 600], "ylim": [-100, 10],
            "overlays": [
                {"type": "contour", "file": UW + "/temperature-0.h5", "dataset": "data",
                 "mesh_file": UW + "/mesh.h5",
                 "levels": [473, 673, 873, 1073], "color": "#ff557f",
                 "clabel": False, "label_region": {}},
                {"type": "scatter", "file": UW + "/plasticStrain-0.h5", "dataset": "data",
                 "cmap": "hot_r", "vmin": 1.5, "vmax": 4.5,
                 "mask_value": {"ge": 1.5}, "mask_y": {"lt": 4}},
                {"type": "field", "file": UW + "/projViscosityField-0.h5", "dataset": "data",
                 "mesh_file": UW + "/mesh.h5", "cmap": "viridis", "alpha": 0.4,
                 "log10": True, "column": 0},
            ],
        }],
    })
    assert len(meta["panels"]) == 1
    assert meta["panels"][0]["kind"] == "material"
check("物质场一图三叠（材质+温度等值线+应变阈值+粘度log10）", t_material)

def t_material_full_overlay():
    # 物质场：材质 + 温度等值线 + 应变散点 + 速度矢量 + 追踪点（grid 系列）
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "material",
            "file": UW + "/swarm-0.h5", "dataset": "data",
            "material_file": UW + "/materialField-0.h5",
            "bg_color": "#404040", "marker_size": 1, "legend": True,
            "xlim": [200, 600], "ylim": [-100, 10],
            "overlays": [
                {"type": "contour", "file": UW + "/temperature-0.h5", "dataset": "data",
                 "mesh_file": UW + "/mesh.h5",
                 "levels": [473, 673, 873, 1073], "color": "#ff557f",
                 "clabel": False, "label_region": {}},
                {"type": "scatter", "file": UW + "/plasticStrain-0.h5", "dataset": "data",
                 "cmap": "hot_r", "vmin": 1.5, "vmax": 4.5,
                 "mask_value": {"ge": 1.5}, "mask_y": {"lt": 4}},
                {"type": "vectors", "file": UW + "/velocityField-0.h5", "dataset": "data",
                 "mesh_file": UW + "/mesh.h5", "color": "#FFFFFF",
                 "stride": 16, "key_uv": 2, "key_text": "2 cm/yr"},
                {"type": "tracers", "file": UW + "/grid1-0.h5", "dataset": "data",
                 "color": "#FFD700", "marker": "o", "size": 1},
            ],
        }],
    })
    assert len(meta["panels"]) == 1
    assert meta["panels"][0]["overlays"]["vectors"] == 1
    assert meta["panels"][0]["overlays"]["tracers"] == 1
check("物质场全叠加（材质+温度+应变+速度矢量+追踪点）", t_material_full_overlay)

def t_overlay_vectors_speed():
    # 速度矢量按大小着色 + colorbar
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "material",
            "file": UW + "/swarm-0.h5", "dataset": "data",
            "material_file": UW + "/materialField-0.h5", "legend": False,
            "overlays": [
                {"type": "vectors", "file": UW + "/velocityField-0.h5", "dataset": "data",
                 "mesh_file": UW + "/mesh.h5", "color": "speed",
                 "cmap": "turbo", "colorbar": True, "cbar_label": "|v| [cm/yr]"},
            ],
        }],
    })
    assert len(meta["panels"]) == 1
check("速度矢量按大小着色（speed + colorbar）", t_overlay_vectors_speed)

def t_overlay_tracers_multi():
    # 多组追踪点（grid1..grid3）不同颜色 + 图例
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "material",
            "file": UW + "/swarm-0.h5", "dataset": "data",
            "material_file": UW + "/materialField-0.h5", "legend": False,
            "overlays": [
                {"type": "tracers",
                 "files": [UW + "/grid1-0.h5", UW + "/grid2-0.h5", UW + "/grid3-0.h5"],
                 "labels": ["grid1", "grid2", "grid3"],
                 "dataset": "data", "legend": True},
            ],
        }],
    })
    assert len(meta["panels"]) == 1
check("多组追踪点叠加（不同颜色+图例）", t_overlay_tracers_multi)

def t_material_filter():
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "material",
            "file": UW + "/swarm-0.h5", "dataset": "data",
            "material_file": UW + "/materialField-0.h5",
            "only_materials": [4, 7], "legend": False,
        }],
    })
    assert len(meta["panels"]) == 1
check("物质场只画材料 4,7（阈值筛选）", t_material_filter)

def t_field():
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "field", "file": UW + "/temperature-0.h5", "dataset": "data",
            "mesh_file": UW + "/mesh.h5", "cmap": "RdBu_r", "colorbar": True,
            "cbar_label": "T [K]", "label": "(a)",
        }],
    })
    assert (P.PLOT_DIR / f"{meta['plot_id']}.png").exists()
    assert len(meta["panels"]) == 1 and meta["panels"][0]["kind"] == "field"
check("场图 temperature-0 (Q1 mesh + colorbar)", t_field)

def t_field_2panel():
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [
            {"kind": "field", "file": UW + "/temperature-0.h5", "dataset": "data",
             "mesh_file": UW + "/mesh.h5", "cmap": "viridis", "label": "(a)"},
            {"kind": "field", "file": UW + "/velocityField-0.h5", "dataset": "data",
             "column": 0, "mesh_file": UW + "/mesh.h5", "cmap": "coolwarm",
             "cbar_label": "Vx [cm/yr]", "label": "(b)"},
        ],
    })
    assert len(meta["panels"]) == 2
    assert P.PLOT_DIR / f"{meta['plot_id']}.pdf"
check("双面板 A4 纵向", t_field_2panel)

def t_layout_2x2_custom_ratios():
    # 2×2 四步物质场 + 自定义行高比（如真实 5:1 横条上下叠）
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "layout": {"rows": 2, "cols": 2, "height_ratios": [3, 2], "width_ratios": [1, 1]},
        "panels": [
            {"kind": "material", "file": UW + "/swarm-50.h5", "dataset": "data",
             "material_file": UW + "/materialField-50.h5", "legend": False},
            {"kind": "material", "file": UW + "/swarm-150.h5", "dataset": "data",
             "material_file": UW + "/materialField-150.h5", "legend": False},
            {"kind": "material", "file": UW + "/swarm-200.h5", "dataset": "data",
             "material_file": UW + "/materialField-200.h5", "legend": False},
            {"kind": "material", "file": UW + "/swarm-250.h5", "dataset": "data",
             "material_file": UW + "/materialField-250.h5", "legend": False},
        ],
    })
    assert len(meta["panels"]) == 4
    ps = sorted(meta["panels"], key=lambda p: p["i"])
    # 行 0 高度 > 行 1 高度（3:2）
    assert ps[0]["h_px"] > ps[2]["h_px"]
check("2×2 四连物质场 + 行高比 3:2", t_layout_2x2_custom_ratios)

def t_layout_4x1():
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "layout": {"rows": 4, "cols": 1},
        "panels": [
            {"kind": "material", "file": UW + f"/swarm-{s}.h5", "dataset": "data",
             "material_file": UW + f"/materialField-{s}.h5", "legend": False}
            for s in (50, 150, 200, 250)
        ],
    })
    assert len(meta["panels"]) == 4
    # 4 行 1 列：左对齐、宽度接近相等
    xs = {round(p["x0_px"]) for p in meta["panels"]}
    assert len(xs) == 1
check("4×1 纵向四连（同列对齐）", t_layout_4x1)

def t_swarm():
    meta = P.render_plot({
        "orientation": "landscape", "style": {},
        "panels": [{
            "kind": "swarm", "file": UW + "/swarm-0.h5", "dataset": "data",
            "x_col": 0, "y_col": 1, "color_by": "material",
            "material_file": UW + "/materialField-0.h5",
            "marker_size": 1, "legend": True,
        }],
    })
    assert len(meta["panels"]) == 1
check("swarm 材料图 (自动下采样)", t_swarm)

def t_curve():
    meta = P.render_plot({
        "orientation": "landscape", "style": {},
        "panels": [{
            "kind": "curve", "file": BD, "dataset": "cumdiff",
            "columns": [0], "xlabel": "node", "ylabel": "cumdiff [m]",
            "legend": False,
        }],
    })
    assert len(meta["panels"]) == 1
check("Badlands 曲线 cumdiff", t_curve)

def t_surfaces_modes():
    # 界面线面板：顶面(每列最高)/底面(每列最低)/全范围散点，列分辨率 60，提取 x 范围
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "surfaces",
            "file": UW + "/swarm-0.h5", "dataset": "data",
            "material_file": UW + "/materialField-0.h5",
            "n_segments": 60, "x_min": 200, "x_max": 600, "legend": True,
            "lines": [
                {"mat": 1, "mode": "min", "label": "Topography", "color": "#1f77b4", "lw": 1.6},
                {"mat": 3, "mode": "max", "label": "Moho", "color": "#d62728", "lw": 1.6},
                {"mat": 4, "mode": "all", "label": "mat4 scatter", "color": "#ff7f0e",
                 "size": 1, "alpha": 0.6},
            ],
        }],
    })
    assert meta["panels"][0]["kind"] == "surfaces"
    assert meta["panels"][0]["lines"] == 3
check("界面线：顶/底面按列极值 + 全范围散点（列分辨率 60）", t_surfaces_modes)

def t_field_mask_contour():
    # 场图：显示范围筛选（区间外留空）+ 固定值等值线列表 + 单数字条数两种写法
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [
            {"kind": "field", "file": UW + "/temperature-0.h5", "dataset": "data",
             "mesh_file": UW + "/mesh.h5", "cmap": "turbo",
             "mask_range": [400, 1000],
             "contour": True, "contour_levels": [500, 700, 900], "clabel": False},
            {"kind": "field", "file": UW + "/temperature-0.h5", "dataset": "data",
             "mesh_file": UW + "/mesh.h5", "cmap": "turbo",
             "contour": True, "contour_levels": 6, "clabel": False},
        ],
    })
    assert len(meta["panels"]) == 2
check("场图显示范围筛选 + 固定值等值线（列表/条数）", t_field_mask_contour)

def t_stress_mask():
    # 应力场（单元中心）：显示范围筛选只画区间内单元 + 应力等值线叠加（单元中心网格）
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "material",
            "file": UW + "/swarm-0.h5", "dataset": "data",
            "material_file": UW + "/materialField-0.h5", "legend": False,
            "overlays": [
                {"type": "contour", "file": UW + "/projStressTensor-0.h5",
                 "dataset": "data", "mesh_file": UW + "/mesh.h5",
                 "levels": [-4, 0, 4], "color": "#00E5FF", "clabel": False,
                 "linewidth": 1.0, "linestyle": "-"},
            ],
        }, {
            "kind": "stress",
            "file": UW + "/projStressTensor-0.h5", "dataset": "data",
            "mesh_file": UW + "/mesh.h5", "column": 1, "cmap": "RdBu_r",
            "vmin": -8, "vmax": 8, "mask_range": [-2, 2],
        }],
    })
    assert len(meta["panels"]) == 2
    assert meta["panels"][0]["overlays"]["contour"] == 1
check("应力场显示范围筛选 + 任意场等值线（单元中心）", t_stress_mask)

def t_overlay_scatter_two_sided():
    # 应变散点双向阈值（值上下限 + y 上下限）+ 场叠加显示范围筛选（原始物理量）
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "material",
            "file": UW + "/swarm-0.h5", "dataset": "data",
            "material_file": UW + "/materialField-0.h5", "legend": False,
            "overlays": [
                {"type": "scatter", "file": UW + "/plasticStrain-0.h5", "dataset": "data",
                 "cmap": "hot_r", "mask_value": {"ge": 1.0, "le": 3.0},
                 "mask_y": {"ge": -60, "lt": 0}},
                {"type": "field", "file": UW + "/projViscosityField-0.h5", "dataset": "data",
                 "mesh_file": UW + "/mesh.h5", "cmap": "viridis", "alpha": 0.4,
                 "log10": True, "column": 0, "mask_range": [1e20, 1e23]},
            ],
        }],
    })
    assert meta["panels"][0]["overlays"]["scatter"] == 1
    assert meta["panels"][0]["overlays"]["field"] == 1
check("应变散点双向阈值 + 场叠加显示范围筛选", t_overlay_scatter_two_sided)

def t_template_2plus1():
    # ultraplot 式模板：第一行 2 列 + 第二行通栏；外底图例/colorbar 不侵入邻面板
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "layout": {"template": "2+1", "height_ratios": "2,1"},
        "panels": [
            {"kind": "material", "file": UW + "/swarm-200.h5",
             "material_file": UW + "/materialField-200.h5",
             "legend": True, "legend_loc": "outside bottom", "legend_ncol": 3,
             "overlays": [{"type": "scatter", "file": UW + "/plasticStrain-200.h5",
                           "cmap": "hot_r", "vmin": 1.5, "vmax": 4.5,
                           "mask_value": {"ge": 1.5}, "colorbar": True}]},
            {"kind": "field", "file": UW + "/temperature-200.h5",
             "mesh_file": UW + "/mesh.h5", "cmap": "turbo"},
            {"kind": "stress", "file": UW + "/projStressTensor-200.h5",
             "mesh_file": UW + "/mesh.h5", "column": 1, "cmap": "RdBu_r",
             "vmin": -8, "vmax": 8},
        ],
    })
    assert meta["layout"]["rows"] == 2 and meta["layout"]["dropped"] == 0
    assert len(meta["panels"]) == 3
    p0, p2 = meta["panels"][0], meta["panels"][2]
    assert p0["y0_px"] >= p2["y0_px"] + p2["h_px"] - 1   # 上下不重叠
check("模板 2+1（行1两列 + 行2通栏，元素不跨面板）", t_template_2plus1)

def t_template_dropped():
    # 容量溢出：2+1 只容 3 个，塞 4 个 → dropped=1
    base = {"kind": "field", "file": UW + "/temperature-200.h5",
            "mesh_file": UW + "/mesh.h5", "cmap": "turbo"}
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "layout": {"template": "2+1"},
        "panels": [dict(base) for _ in range(4)],
    })
    assert meta["layout"]["dropped"] == 1
    assert len(meta["panels"]) == 3
check("模板容量溢出 dropped 计数", t_template_dropped)

def t_qgis_cmaps():
    # 本地 QGIS 配色库（用户 profile DB / 自带 XML）→ 可作场图色板
    from core import qgis_cmaps as QG
    ramps = QG.load_qgis_ramps(force=True)
    if not ramps:
        print("  (本机无 QGIS，跳过)")
        return
    assert len(ramps) > 50
    assert all(len(v) == 16 and v[0].startswith("#") for v in list(ramps.values())[:10])
    name = sorted(ramps)[5]
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{"kind": "field", "file": UW + "/temperature-0.h5",
                    "mesh_file": UW + "/mesh.h5", "cmap": name}],
    })
    assert meta["panels"][0]["kind"] == "field"
check("QGIS 配色库加载 + 场图渲染", t_qgis_cmaps)

def t_box_ratio_169():
    # 盒比例预设 16:9 + fig3/S4 式四行两列模板
    base = {"kind": "field", "file": UW + "/temperature-200.h5",
            "mesh_file": UW + "/mesh.h5", "cmap": "turbo", "aspect": "16:9",
            "colorbar": False}
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "layout": {"template": "2+2+2+2"},
        "panels": [dict(base) for _ in range(8)],
    })
    assert len(meta["panels"]) == 8 and meta["layout"]["dropped"] == 0
    p0 = meta["panels"][0]
    assert abs(p0["w_px"] / p0["h_px"] - 16 / 9) < 0.06
    # 4:3 单面板
    meta2 = P.render_plot({"orientation": "portrait", "style": {},
        "panels": [{**base, "aspect": "4:3"}]})
    q0 = meta2["panels"][0]
    assert abs(q0["w_px"] / q0["h_px"] - 4 / 3) < 0.06
check("盒比例 16:9/4:3 + 四行两列模板", t_box_ratio_169)

print("== 3. probe 点击读数 ==")
from core import probe

def t_probe_material():
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "material",
            "file": UW + "/swarm-0.h5", "dataset": "data",
            "material_file": UW + "/materialField-0.h5",
            "xlim": [0, 800], "ylim": [-150, 10], "legend": False,
        }],
    })
    p = meta["panels"][0]
    px = p["x0_px"] + p["w_px"] / 2
    H = int(11.69 * meta["dpi"])
    py = H - p["y0_px"] - p["h_px"] / 2   # 前端顶原点坐标
    r = probe.probe(meta["plot_id"], px, py, int(8.27 * meta["dpi"]), H)
    assert r["hit"] and "material" in r["values"] and "mat_name" in r["values"]
check("物质场探针（最近粒子材料 id/名称）", t_probe_material)

def t_probe_field():
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{
            "kind": "field", "file": UW + "/temperature-0.h5", "dataset": "data",
            "mesh_file": UW + "/mesh.h5", "cmap": "RdBu_r", "colorbar": False,
        }],
    })
    p = meta["panels"][0]
    # 点击面板中心（顶原点，与前端一致）
    px = p["x0_px"] + p["w_px"] / 2
    H = int(11.69 * meta["dpi"])
    py = H - p["y0_px"] - p["h_px"] / 2
    r = probe.probe(meta["plot_id"], px, py, int(8.27 * meta["dpi"]), H)
    assert r["hit"] and "value" in r["values"]
    assert -150 <= r["y"] <= 10 and 0 <= r["x"] <= 800
check("场图探针（返回数据坐标+值）", t_probe_field)

def t_probe_swarm():
    meta = P.render_plot({
        "orientation": "landscape", "style": {},
        "panels": [{
            "kind": "swarm", "file": UW + "/swarm-0.h5", "dataset": "data",
            "x_col": 0, "y_col": 1, "color_by": "material",
            "material_file": UW + "/materialField-0.h5",
        }],
    })
    p = meta["panels"][0]
    px = p["x0_px"] + p["w_px"] / 2
    H = int(8.27 * meta["dpi"])
    py = H - p["y0_px"] - p["h_px"] / 2
    r = probe.probe(meta["plot_id"], px, py, int(11.69 * meta["dpi"]), H)
    assert r["hit"] and "nearest_index" in r["values"]
check("swarm 探针（最近粒子索引/数值列）", t_probe_swarm)

print("== 4. 导出 ==")
import shutil, tempfile, os
from core import config as C

def t_export():
    meta = P.render_plot({
        "orientation": "portrait", "style": {},
        "panels": [{"kind": "curve", "file": BD, "dataset": "cumdiff", "columns": [0]}],
    })
    # 高分辨率产物按需生成（提速后的延迟渲染路径）
    assert P.ensure_hi_res(meta["plot_id"])
    assert (C.PLOT_DIR / f"{meta['plot_id']}.pdf").exists()
    assert (C.PLOT_DIR / f"{meta['plot_id']}.png300.png").exists()
    tmp = Path(tempfile.mkdtemp(prefix="h5plot_export_"))
    for suffix, src in [("png", "png300.png"), ("pdf", "pdf"), ("svg", "svg")]:
        shutil.copy2(C.PLOT_DIR / f"{meta['plot_id']}.{src}", tmp / f"demo.{suffix}")
    sizes = {s: (tmp / f"demo.{s}").stat().st_size for s in ("png", "pdf", "svg")}
    shutil.rmtree(tmp)
    assert all(v > 0 for v in sizes.values())
check("导出三件套 (PNG300/PDF/SVG, 按需生成)", t_export)

print(f"\n结果: {ok} 通过, {fail} 失败")
sys.exit(1 if fail else 0)