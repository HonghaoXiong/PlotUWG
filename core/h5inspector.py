"""H5 检视器：树状结构、数据集元信息、采样预览、文件类型识别。

只读操作；对超大数据集（如 512 万粒子 swarm）只做均匀采样统计，
绝不整读，保证大文件也能秒开。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import h5py
import numpy as np

SAMPLE_HEAD_ROWS = 8      # 密集表头预览行数
STATS_MAX_POINTS = 200_000  # 统计用采样点数上限


def is_h5(path: str) -> bool:
    _, ext = os.path.splitext(path)
    return ext.lower() in {".h5", ".hdf5", ".hdf", ".he5"}


def sibling_xmf(path: str) -> str | None:
    """同目录同名 .xmf 描述文件（UW2 场数据常与 XDMF 成对）。"""
    p = Path(path)
    cand = p.with_suffix(".xmf")
    if cand.exists():
        return cand.name
    return None


def detect_file_type(path: str, keys: list[str]) -> str:
    name = Path(path).name.lower()
    if name.startswith("tin.") and name.endswith((".hdf5", ".h5")):
        return "badlands"
    if "vertices" in keys and "en_map" in keys:
        return "mesh"
    if name.startswith("swarm") or any(k.startswith("swarm") for k in keys):
        return "swarm"
    if name.startswith("mesh"):
        return "mesh"
    for pref in ("material", "temperature", "velocity", "pressure", "strain", "plastic", "viscosity", "density", "stress", "time", "proj"):
        if name.startswith(pref):
            return "field"
    return "generic"


def _sample_stats(ds: h5py.Dataset) -> dict:
    """对数值型 dataset 做均匀采样统计（不整读，分段块读避免随机索引）。"""
    n = ds.shape[0]
    if n == 0:
        return {}
    if n <= STATS_MAX_POINTS:
        arr = ds[()] if ds.ndim == 1 else ds[:]
        arr = np.asarray(arr)
    else:
        # 前/中/后三段块读（strided slice 在 HDF5 上同样是块级读取）
        seg = STATS_MAX_POINTS // 3
        seg = min(seg, n)
        mid = n // 2
        pieces = [ds[:seg], ds[mid:mid + seg], ds[n - seg:]]
        arr = np.concatenate([np.asarray(p).reshape(-1) for p in pieces])
    flat = arr.reshape(-1).astype(np.float64)
    finite = flat[np.isfinite(flat)]
    if finite.size == 0:
        return {}
    return {
        "min": round(float(finite.min()), 6),
        "max": round(float(finite.max()), 6),
        "mean": round(float(finite.mean()), 6),
        "nan_fraction": round(float(1 - finite.size / flat.size), 6),
    }


def _sample_head(ds: h5py.Dataset, max_rows: int = SAMPLE_HEAD_ROWS,
                 max_cols: int = 8) -> list:
    """前几行预览（大数组仅取前几行）。"""
    try:
        if ds.ndim == 0:
            v = ds[()]
            v = v.item() if hasattr(v, "item") else v
            return v
        nrows = min(ds.shape[0], max_rows)
        if ds.ndim == 1:
            arr = ds[:nrows]
        else:
            ncols = min(ds.shape[1], max_cols)
            arr = ds[:nrows, :ncols]
        arr = np.asarray(arr)
        rows = []
        for i in range(nrows):
            row = arr[i]
            vals = []
            if hasattr(row, "shape") and row.ndim > 0:
                for v in row:
                    if isinstance(v, (np.floating, float)):
                        vals.append(round(float(v), 6))
                    else:
                        vals.append(v.item() if hasattr(v, "item") else v)
            else:
                v = row
                vals.append(round(float(v), 6) if isinstance(v, (np.floating, float)) else v)
            rows.append(vals)
        return rows
    except Exception as e:  # noqa: BLE001
        return [{"error": str(e)}]


def _shape_preview(ds: h5py.Dataset) -> list:
    """shape 数值 + 语义（如 '5120000 particles × 2 coords'）。"""
    if ds.ndim == 0:
        return "scalar"
    parts = list(ds.shape)
    if len(parts) == 1:
        return f"{parts[0]:,}"
    return ", ".join(f"{p:,}" for p in parts)


def inspect_h5_file(path: str) -> dict:
    """返回 h5 文件的完整结构信息。"""
    result = {
        "path": path,
        "filename": Path(path).name,
        "size_bytes": os.path.getsize(path),
        "is_h5": True,
        "root_attrs": {},
        "type": "generic",
        "tree": [],
        "n_datasets": 0,
        "n_groups": 0,
        "xmf_sibling": sibling_xmf(path),
        "error": None,
    }
    try:
        with h5py.File(path, "r") as f:
            result["root_attrs"] = _attrs_to_jsonable(f.attrs)
            keys = list(f.keys())
            result["type"] = detect_file_type(path, keys)
            _walk_group(f, "", result["tree"], result, depth=0)
    except Exception as e:  # noqa: BLE001
        result["error"] = str(e)
        result["is_h5"] = False
    return result


def _attrs_to_jsonable(attrs) -> dict:
    out = {}
    for k, v in attrs.items():
        try:
            if isinstance(v, np.ndarray):
                if v.size > 200:
                    out[k] = f"<ndarray shape={v.shape} dtype={v.dtype}>"
                else:
                    out[k] = v.tolist()
            else:
                vv = v.item() if hasattr(v, "item") else v
                if isinstance(vv, bytes):
                    vv = vv.decode("utf-8", errors="replace")
                out[k] = vv
        except Exception:  # noqa: BLE001
            out[k] = "<unreadable>"
    return out


def _walk_group(f: h5py.File, name: str, out: list, result: dict, depth: int) -> None:
    if name:
        grp = f[name]
    else:
        grp = f
    for key in grp.keys():
        obj = grp[key]
        node = {"name": key, "path": f"{name}/{key}" if name else key, "depth": depth + 1}
        if isinstance(obj, h5py.Group):
            node["kind"] = "group"
            node["attrs"] = _attrs_to_jsonable(obj.attrs)
            node["children"] = []
            result["n_groups"] += 1
            _walk_group(f, node["path"], node["children"], result, depth + 1)
        elif isinstance(obj, h5py.Dataset):
            result["n_datasets"] += 1
            ds = obj
            node["kind"] = "dataset"
            node["shape"] = _shape_preview(ds)
            node["shape_raw"] = list(ds.shape) if ds.ndim else None
            node["ndim"] = ds.ndim
            node["dtype"] = str(ds.dtype)
            node["bytes"] = ds.size * ds.dtype.itemsize
            node["attrs"] = _attrs_to_jsonable(ds.attrs)
            node["compression"] = getattr(ds, "compression", None)
            node["chunks"] = str(ds.chunks) if ds.chunks else None
            dk = ds.dtype.kind
            node["stats"] = _sample_stats(ds) if dk in "fc" else {}
            node["head"] = _sample_head(ds)
            out.append(node)
        else:
            out.append(node)


def directory_listing(path: str, limit: int = 5000) -> dict:
    """列目录：子目录 + 支持读取的 h5 文件（系列文件折叠分组）+ 其他文件数量。

    大目录（如 uw217 输出 4000+ 文件）会把 `NAME-NNN.h5` 系列折叠成
    可展开分组（至少 3 个同前缀才折叠），避免前面几百个 grid 文件把
    swarm/materialField 等挤到列表外。
    """
    p = Path(os.path.expanduser(path)).resolve()
    out = {"path": str(p), "parent": str(p.parent) if p.parent else None,
           "exists": p.exists(), "is_dir": p.is_dir(), "items": [], "error": None}
    if not p.exists() or not p.is_dir():
        if not p.exists() and p.is_file():
            out["is_dir"] = False
            return out
        out["error"] = "路径不存在或不是目录"
        return out
    try:
        entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError as e:
        out["error"] = f"无权限: {e}"
        return out
    h5s: list[dict] = []
    dirs: list[dict] = []
    n_other = 0
    for e in entries:
        if e.is_dir():
            dirs.append({"name": e.name, "path": str(e), "is_dir": True,
                         "is_h5": False})
        elif is_h5(e.name):
            h5s.append({"name": e.name, "path": str(e), "is_dir": False,
                        "is_h5": True, "bytes": os.path.getsize(e)})
        else:
            n_other += 1
    out["n_other"] = n_other
    out["items"] = dirs[:limit] + _fold_h5_series(h5s, limit=max(limit - len(dirs), 0))
    return out


_STEP_RE = re.compile(r"^(.*?)-([0-9]+)\.(h5|hdf5|hdf)$", re.IGNORECASE)

MODEL_FIELD_ALIASES = {
    "swarm": "swarm", "materialField": "material", "temperature": "temperature",
    "plasticStrain": "strain", "projViscosityField": "viscosity",
    "velocityField": "velocity", "projVelocityField": "velocity",
    "pressureField": "pressure", "strainRateField": "strainRate",
    "meltField": "melt", "projStressTensor": "stressTensor",
    "projDensityField": "density", "projMaterialField": "projMaterial",
    "projPlasticStrain": "projStrain", "timeField": "time",
    "passiveTracers": "tracers", "tracers": "tracers",
    "topographyField": "topography",
}

_GRID_RE = re.compile(r"^grid(\d+)-([0-9]+)\.(h5|hdf5|hdf)$", re.IGNORECASE)


def scan_model_dir(path: str) -> dict:
    """扫描模型输出目录中的 NAME-N.h5 系列，返回时间步与字段结构。

    用于“时间自动对齐”：swarm/materialField/temperature/plasticStrain 等
    同一 step 的文件自动配对。
    """
    p = Path(os.path.expanduser(path)).resolve()
    out = {"path": str(p), "is_model_dir": False, "fields": {}, "steps": [],
           "tracer_groups": [], "time_units": None, "time_scale_myr": None,
           "has_mesh": (p / "mesh.h5").exists() or (p / "Mesh.h5").exists(),
           "error": None}
    if not p.is_dir():
        out["error"] = "路径不是目录"
        return out
    field_steps: dict[str, list[int]] = {}
    tracer_groups: dict[str, set[int]] = {}
    try:
        for e in p.iterdir():
            if not e.is_file() or not is_h5(e.name):
                continue
            mg = _GRID_RE.match(e.name)
            if mg:
                try:
                    tracer_groups.setdefault(mg.group(1), set()).add(int(mg.group(2)))
                except ValueError:
                    pass
                continue
            m = _STEP_RE.match(e.name)
            if not m:
                continue
            try:
                step = int(m.group(2))
            except ValueError:
                continue
            field_steps.setdefault(m.group(1), []).append(step)
    except OSError as ex:
        out["error"] = str(ex)
        return out
    if not field_steps:
        return out
    for k in field_steps:
        field_steps[k].sort()
    # 只看与模型高频输出匹配的字段
    important = {k: v for k, v in field_steps.items()
                 if k in MODEL_FIELD_ALIASES or k.startswith(("grid", "field"))}
    steps = sorted(set().union(*important.values())) if important else []
    out["fields"] = {k: {"alias": MODEL_FIELD_ALIASES.get(k, k), "steps": field_steps[k]}
                      for k in field_steps
                      if k in MODEL_FIELD_ALIASES}
    out["steps"] = steps
    out["tracer_groups"] = [
        {"prefix": k, "steps": sorted(v)} for k, v in sorted(
            tracer_groups.items(), key=lambda kv: (len(kv[0]), kv[0]))
    ]
    # 真实时间：从 timeField/projTimeField 读取（UW2 默认单位=年；值/1e6 = Myr）
    # 读首末两个时间点，前端按线性插值换算每个 step 的真实时间
    try:
        tf_cand = next((k for k in ("timeField", "projTimeField") if k in field_steps), None)
        if tf_cand and field_steps[tf_cand]:
            steps_tf = sorted(field_steps[tf_cand])
            s0, s1 = steps_tf[0], steps_tf[-1]
            def _read_time(step: int) -> float:
                with h5py.File(str(p / f"{tf_cand}-{step}.h5"), "r") as f:
                    return float(np.asarray(f["data"][:1], dtype=float).reshape(-1)[0])
            t0 = _read_time(s0)
            t1 = _read_time(s1) if s1 != s0 else t0
            if np.isfinite(t0) and np.isfinite(t1):
                out["time_units"] = "yr"
                out["time_scale_myr"] = 1e6
                out["step_start"] = s0
                out["step_end"] = s1
                out["time_start"] = float(t0)
                out["time_end"] = float(t1)
    except Exception:  # noqa: BLE001
        pass
    out["is_model_dir"] = len(steps) >= 2 and "materialField" in out["fields"]
    return out


def _series_key(name: str) -> tuple:
    m = _STEP_RE.match(name)
    if m:
        return (0, int(m.group(2)))
    return (1, 0)


def _fold_h5_series(files: list[dict], limit: int, min_group: int = 3) -> list[dict]:
    """把 NAME-NNN.h5 系列折叠为分组（>= min_group 个才折叠）。"""
    groups: dict[str, list[dict]] = {}
    singles: list[dict] = []
    for f in files:
        m = _STEP_RE.match(f["name"])
        if m:
            groups.setdefault(m.group(1), []).append(f)
        else:
            singles.append(f)
    items: list[dict] = []
    for k, fs in sorted(groups.items()):
        fs.sort(key=lambda e: _series_key(e["name"]))
        if len(fs) >= min_group:
            ext = fs[0]["name"].rsplit(".", 1)[-1]
            items.append({
                "name": f"{k}-*.{ext}", "path": str(Path(fs[0]["path"]).parent),
                "is_dir": False, "is_h5": False, "group": True,
                "count": len(fs),
                "bytes": sum(x["bytes"] for x in fs),
                "children": fs,
            })
        else:
            singles.extend(fs)
    singles.sort(key=lambda e: e["name"].lower())
    all_items = singles + items
    # grid* 系列（剖分网格中间产物）排到列表末尾，常用场/粒子文件优先
    all_items.sort(key=lambda it: (1 if it["name"].lower().startswith("grid") else 0,
                                   it["name"].lower()))
    return all_items[:limit]