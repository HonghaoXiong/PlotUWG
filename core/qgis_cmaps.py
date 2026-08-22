"""本地 QGIS 配色库接入：用户 profile 的 symbology-style.db + App 自带 symbology-style.xml。

把 QGIS colorramp（gradient 带 stops / preset 显式色列）转换为 16 点 hex 渐变，
供后端 _resolve_cmap 与前端色板下拉/预览条使用。无 QGIS 时优雅返回空。
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import numpy as np
from matplotlib.colors import LinearSegmentedColormap

RAMPS: dict[str, list[str]] = {}      # name -> 16 点 hex
CMAPS: dict[str, LinearSegmentedColormap] = {}
_LOADED = False


def _hex_from_qgis(v: str) -> str | None:
    p = (v or "").split(",")
    try:
        r, g, b = (int(float(x)) for x in p[:3])
    except (ValueError, IndexError):
        return None
    return f"#{r:02x}{g:02x}{b:02x}"


def _props(xml: str) -> dict[str, str]:
    """<Option value="..." name="..."/> → {name: value}"""
    return {n: v for v, n in re.findall(r'<Option\s+value="([^"]*)"\s+name="([^"]*)"', xml)}


def _sample(stops: list[tuple[float, str]], n: int = 16) -> list[str]:
    """(pos, hex) 分段线性采样为 n 点 hex 列。"""
    stops = sorted(stops, key=lambda t: t[0])
    pos = np.array([p for p, _ in stops], dtype=float)
    rgb = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for _, h in stops], dtype=float)
    xs = np.linspace(0.0, 1.0, n)
    out = []
    for x in xs:
        c = np.clip(np.interp(x, pos, rgb[:, 0]), 0, 255).astype(int)
        g = np.clip(np.interp(x, pos, rgb[:, 1]), 0, 255).astype(int)
        b = np.clip(np.interp(x, pos, rgb[:, 2]), 0, 255).astype(int)
        out.append(f"#{c:02x}{g:02x}{b:02x}")
    return out


def parse_ramp_xml(xml: str) -> list[str] | None:
    """gradient（color1/color2/stops）或 preset（preset_color_N）→ 16 点 hex。"""
    props = _props(xml)
    if props.get("rampType", "") == "preset" or any(k.startswith("preset_color_") for k in props):
        cols = []
        for i in range(200):
            v = props.get(f"preset_color_{i}")
            if v is None:
                break
            h = _hex_from_qgis(v)
            if h:
                cols.append(h)
        if len(cols) < 2:
            return None
        return _sample([(i / (len(cols) - 1), h) for i, h in enumerate(cols)])
    # gradient
    c1 = _hex_from_qgis(props.get("color1", ""))
    c2 = _hex_from_qgis(props.get("color2", ""))
    if not c1 or not c2:
        return None
    stops = [(0.0, c1), (1.0, c2)]
    for seg in (props.get("stops") or "").split(":"):
        parts = seg.split(";")
        if len(parts) >= 2:
            try:
                off = float(parts[0])
            except ValueError:
                continue
            h = _hex_from_qgis(parts[1])
            if h and 0.0 < off < 1.0:
                stops.append((off, h))
    return _sample(stops)


def _load_db(db: Path, out: dict, add=None) -> int:
    n = 0
    try:
        con = sqlite3.connect(str(db))
        for _name, xml in con.execute("select name, xml from colorramp"):
            hexes = parse_ramp_xml(xml or "")
            if add is not None:
                before = len(out)
                add(_name, hexes or [])
                n += len(out) - before
            elif _name not in out and hexes:
                out[_name] = hexes
                n += 1
        con.close()
    except Exception:  # noqa: BLE001
        pass
    return n


def _load_xml_file(path: Path, out: dict, add=None) -> int:
    n = 0
    try:
        text = path.read_text("utf-8", errors="ignore")
        for m in re.finditer(r"<colorramp\b.*?</colorramp>", text, re.S):
            block = m.group(0)
            nm = re.search(r'name="([^"]+)"', block)
            if not nm:
                continue
            hexes = parse_ramp_xml(block)
            if add is not None:
                before = len(out)
                add(nm.group(1), hexes or [])
                n += len(out) - before
            elif nm.group(1) not in out and hexes:
                out[nm.group(1)] = hexes
                n += 1
    except Exception:  # noqa: BLE001
        pass
    return n


def load_qgis_ramps(force: bool = False) -> dict[str, list[str]]:
    """QGIS 配色库：内置打包数据优先（任何机器都有），再叠加本机 QGIS 用户自定义。

    内置 core/data/qgis_colormaps.json 由 tools/build_qgis_colormaps.py 在构建期
    从 QGIS 默认 XML + cpt-city 全量渐变 + 构建机用户收藏导出。
    与 matplotlib 内置同名（忽略大小写）剔除；重名忽略大小写去重。"""
    global _LOADED
    if _LOADED and not force:
        return RAMPS
    _LOADED = True
    import matplotlib as _mpl
    mpl_lower = {n.lower() for n in _mpl.colormaps}
    out: dict[str, list[str]] = {}
    seen: set[str] = set()

    def _add(name: str, hexes: list[str]) -> None:
        low = (name or "").lower()
        if not hexes or not low or low in mpl_lower or low in seen:
            return
        seen.add(low)
        out[name] = hexes

    # 1) 内置打包（随软件分发）
    data_file = Path(__file__).resolve().parent / "data" / "qgis_colormaps.json"
    if data_file.exists():
        try:
            doc = json.loads(data_file.read_text("utf-8"))
            for name, hexes in (doc.get("ramps") or {}).items():
                _add(name, hexes)
        except Exception:  # noqa: BLE001
            pass
    # 2) 叠加本机 QGIS 用户配置（构建后新增的自定义配色）
    sup = Path.home() / "Library" / "Application Support" / "QGIS"
    for db in sorted(sup.glob("*/profiles/default/symbology-style.db"), reverse=True):
        _load_db(db, out, _add)
    RAMPS.clear()
    RAMPS.update(out)
    CMAPS.clear()
    for name, hexes in RAMPS.items():
        try:
            CMAPS[name] = LinearSegmentedColormap.from_list(f"qgis-{name}", hexes, 256)
        except Exception:  # noqa: BLE001
            pass
    return RAMPS


def get_cmap(name: str) -> LinearSegmentedColormap | None:
    if not _LOADED:
        load_qgis_ramps()
    return CMAPS.get(name)
