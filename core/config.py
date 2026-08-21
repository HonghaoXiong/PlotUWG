"""H5Plot Studio 配置：A4 画板预设、样式默认值、绘图配置持久化。

默认值直接取自用户的论文绘图习惯（plot_model_setup.py /
plot_basin_orogen_convergence_partition.py，2026-08 核验）：
- A4 画板（纵向 8.27 x 11.69 in / 横向 11.69 x 8.27 in）
- Arial 字体、7-9 pt 正文、tick 朝内、线宽 0.75 pt、细脊柱
- 输出 PNG 300 dpi + PDF + SVG（svg.fonttype='none'）
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if getattr(sys, "frozen", False):
    # 打包 App：userdata 放用户目录（bundle 内只读）
    APP_DIR = Path.home() / "Library" / "Application Support" / "H5TOUWG"
CONFIG_DIR = APP_DIR / "userdata"
CONFIG_FILE = CONFIG_DIR / "plot_config.json"
RECENT_FILE = CONFIG_DIR / "recent_paths.json"
PLOT_DIR = CONFIG_DIR / "rendered"          # 渲染中间产物（预览 PNG/SVG/probe 数据）
PLOT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# A4 画板预设（英寸）
# --------------------------------------------------------------------------
A4 = {
    "portrait": {"width": 8.27, "height": 11.69, "label": "A4 纵向 (210×297 mm)"},
    "landscape": {"width": 11.69, "height": 8.27, "label": "A4 横向 (297×210 mm)"},
}

# --------------------------------------------------------------------------
# 期刊风格默认样式（用户习惯）
# --------------------------------------------------------------------------
JOURNAL_STYLE = {
    "font_family": "Arial",
    "font_size": 7,          # 正文 pt
    "axes_label_size": 8,
    "title_size": 8,
    "legend_size": 6.5,
    "tick_size": 7,
    "tick_direction": "in",
    "axes_linewidth": 0.75,
    "spines": "thin",        # 隐藏 top/right
    "svg_fonttype": "none",  # 保持 SVG 文本可编辑
    "png_dpi": 300,
    "marker_size": 1,
    "marker_edge_width": 0.4,
}

# 常用定性/连续色板（前端展示用缩略名）
COLORMAPS = {
    "qualitative": [
        # 用户惯用定性色（用于材料/曲线）
        {"name": "Journal (habit)", "type": "qual", "values": ["#2878B5", "#D97924", "#2CA02C", "#D7191C", "#444444", "#2C7BB6", "#DE8F21", "#9D9FE3", "#32583F"]},
        # Qaidam 物质场默认配色（用户惯例，2026-08 核验自 plot_model_setup.py / Myfig_4steps.py）
        {"name": "Qaidam", "type": "qual", "values": ["#F8DB83", "#FCFCFA", "#F7EDD9", "#9D9FE3", "#B8BCE3", "#32583F", "#DE8F21", "#BEBFCB", "#B2D6CC", "#404040"]},
        {"name": "Earth Structure", "type": "qual", "values": ["#D9D9FF", "#EE650A", "#FCD97A", "#37889F", "#3260A4", "#83CC92"]},
        {"name": "Set1", "type": "qual", "values": list("") or None},
        {"name": "tab10", "type": "qual", "values": None},
        {"name": "Dark2", "type": "qual", "values": None},
    ],
    "sequential": ["viridis", "plasma", "inferno", "magma", "cividis", "turbo", "coolwarm", "RdBu_r", "hot_r", "hot", "Blues", "Oranges", "Greens", "Reds", "bone", "gray"],
}

# Qaidam 物质场配色：material id → hex（用户论文常用，含 Air/LM 背景色）
QAIDAM_MATERIAL_COLORS = {
    1: "#FCFCFA",  # Air
    2: "#F8DB83",  # Sed
    3: "#F7EDD9",  # Lithospheric Mantle
    4: "#9D9FE3",  # Qaidam UC
    5: "#B8BCE3",  # Qaidam MC
    6: "#32583F",  # Qaidam LC
    7: "#DE8F21",  # Orogen UC
    8: "#BEBFCB",  # Orogen MC
    9: "#B2D6CC",  # Orogen LC
}

# Earth Structure 步进色标（geology_colorbar.json 提取，1..6 材料）
EARTH_STRUCTURE_COLORS = {
    1: "#D9D9FF",  # 空气 浅灰
    2: "#EE650A",  # 沉积物 橙色 (0.933,0.394,0.04)
    3: "#FCD97A",  # 上地壳 蛋黄色
    4: "#37889F",  # 柴达木下地壳 蓝绿 (0.215,0.535,0.648)
    5: "#3260A4",  # 造山带下地壳 深蓝 (0.195,0.375,0.644)
    6: "#83CC92",  # 岩石圈地幔 草绿 (0.515,0.8,0.574)
}

MATERIAL_NAME_PRESETS = {
    "Qaidam": QAIDAM_MATERIAL_COLORS,
    "EarthStructure": EARTH_STRUCTURE_COLORS,
}

MATERIAL_NAMES = {
    1: "Air", 2: "Sed", 3: "LM", 4: "Qaidam UC", 5: "Qaidam MC",
    6: "Qaidam LC", 7: "Orogen UC", 8: "Orogen MC", 9: "Orogen LC",
}


def default_plot_config() -> dict:
    return {
        "orientation": "portrait",
        "style": dict(JOURNAL_STYLE),
        "panel": {
            "gap": 0.55,
            "show_panel_labels": True,
            "panel_label_size": 10,
            "panel_label_weight": "bold",
        },
    }


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text("utf-8"))
            d = default_plot_config()
            d.update(cfg)
            return d
        except Exception:
            pass
    return default_plot_config()


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


def load_recent_paths() -> list[str]:
    if RECENT_FILE.exists():
        try:
            return json.loads(RECENT_FILE.read_text("utf-8"))[:10]
        except Exception:
            pass
    return []


def save_recent_path(path: str) -> None:
    paths = load_recent_paths()
    if path in paths:
        paths.remove(path)
    paths.insert(0, path)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    RECENT_FILE.write_text(json.dumps(paths[:10], ensure_ascii=False, indent=2), "utf-8")


def clear_rendered() -> None:
    """清空中间渲染产物（不影响任何模型输出）。"""
    for f in PLOT_DIR.glob("*"):
        try:
            if f.is_file():
                f.unlink()
        except OSError:
            pass