#!/usr/bin/env python3
"""构建期导出 QGIS 全量配色 → core/data/qgis_colormaps.json（随软件分发）。

来源（按序，重名忽略大小写去重；与 matplotlib 内置同名剔除）：
  1. QGIS App 自带默认 symbology-style.xml（36 个默认 ramp）
  2. cpt-city-qgis-min 渐变档案（5000+ SVG linearGradient）
  3. 构建机用户 profile symbology-style.db（自定义/收藏，如 Pokémon 系列）

用法（geopixel 环境）：python tools/build_qgis_colormaps.py [qgis-app-path]
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from core.qgis_cmaps import _sample, parse_ramp_xml  # noqa: E402

DEFAULT_APP = "/Applications/QGIS-final-4_2_1.app"


def _svg_stops(path: Path) -> list[str] | None:
    try:
        text = path.read_text("utf-8", errors="ignore")
    except OSError:
        return None
    stops = []
    for m in re.finditer(r'<stop\s+([^>]*?)/>', text):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        off = attrs.get("offset", "")
        col = attrs.get("stop-color", "")
        try:
            o = float(off.rstrip("%")) / (100.0 if off.endswith("%") else 1.0)
        except ValueError:
            continue
        if not col.startswith("#"):
            continue
        if len(col) == 4:  # #rgb → #rrggbb
            col = "#" + "".join(c * 2 for c in col[1:])
        if len(col) >= 7:
            stops.append((max(0.0, min(1.0, o)), col[:7]))
    if len(stops) < 2:
        return None
    return _sample(stops, 16)


def main() -> None:
    app = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_APP)
    import matplotlib as mpl
    mpl_lower = {n.lower() for n in mpl.colormaps}
    out: dict[str, list[str]] = {}
    seen: set[str] = set()

    def add(name: str, hexes: list[str] | None) -> None:
        if not hexes or not name:
            return
        low = name.lower()
        if low in mpl_lower or low in seen:
            return
        seen.add(low)
        out[name] = hexes

    res = app / "Contents" / "Resources" / "qgis" / "resources"

    # 1) 默认 XML
    xml = res / "symbology-style.xml"
    if xml.exists():
        for m in re.finditer(r"<colorramp\b.*?</colorramp>", xml.read_text("utf-8", "ignore"), re.S):
            nm = re.search(r'name="([^"]+)"', m.group(0))
            if nm:
                add(nm.group(1), parse_ramp_xml(m.group(0)))
    n_default = len(out)

    # 2) cpt-city SVG 全量
    n_cpt = 0
    base = res / "cpt-city-qgis-min"
    if base.exists():
        for svg in sorted(base.rglob("*.svg")):
            hexes = _svg_stops(svg)
            if hexes:
                before = len(out)
                add("cpt/" + svg.relative_to(base).with_suffix("").as_posix(), hexes)
                n_cpt += len(out) - before

    # 3) 用户 profile DB（自定义/收藏）
    n_user = 0
    sup = Path.home() / "Library" / "Application Support" / "QGIS"
    for db in sorted(sup.glob("*/profiles/default/symbology-style.db"), reverse=True):
        try:
            con = sqlite3.connect(str(db))
            for name, x in con.execute("select name, xml from colorramp"):
                before = len(out)
                add(name, parse_ramp_xml(x or ""))
                n_user += len(out) - before
            con.close()
        except Exception:  # noqa: BLE001
            pass

    dest = ROOT / "core" / "data" / "qgis_colormaps.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"version": 1, "source": str(app.name), "ramps": out},
                               ensure_ascii=False), "utf-8")
    print(f"defaults={n_default} cpt-city={n_cpt} user={n_user} total={len(out)} -> {dest} "
          f"({dest.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
