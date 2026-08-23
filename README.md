# PlotUWG

**PlotUWG** (*Plot Underworld Geodynamics*) is a local desktop tool for visualizing **Underworld 2** and **Badlands** numerical simulation outputs (HDF5/H5). It browses model output directories, auto-detects time steps, and produces **publication-ready A4 figures** (PNG 300dpi + PDF + SVG) with journal-style defaults — all through a modern glassmorphism UI, no Python scripting required.

> Designed for geomodelling researchers: load a model folder, pick a time step, click to plot, export three formats. Everything is a button — no code.

## Features

### 🗂 Model folder intelligence
- Load a **complete model output folder**; all `name-N.h5` series are auto-detected (`swarm`, `materialField`, `temperature`, `plasticStrain`, `velocityField`, `projViscosityField`, `stressField`, `gridN` passive tracers, ...)
- **Real time from the raw H5 files**: reads `timeField`/`projTimeField` and shows true model time (Myr) per step (e.g. step 200 → 20.0 Myr)
- Auto time-step bar: one click to switch any step across all fields

### 📊 A4 plot studio
- **Journal-standard defaults measured from the author's published A4 figures**:
  Arial, ticks 7pt, axis labels 9pt, bold 12pt panel letters, spines 0.6pt,
  data curves 0.2-0.5pt; aspect presets **data-equal / 4:3 / 16:9** / custom;
  `2+2+2+2` template for fig3/S4-style multi-row strip layouts
- **Layout templates (ultraplot-style)**: irregular grids like `2+1` / `4+1` / `3+2`
  (row-1 two columns + row-2 full-width, etc.) via a visual template gallery;
  auto template by panel count; row-height ratios (`3,1`); outside legends &
  colorbars are reserved **inside each panel's grid cell** so elements never
  stack onto neighbouring panels; overflow panels counted as `dropped`
- **Material field** base layer (swarm + materialField) with the **Qaidam palette** (Air / Sed / Lithospheric Mantle / Qaidam UC-MC-LC / Orogen UC-MC-LC, matched to the paper convention)
- **Interface lines panel** — pick any material index and draw its **top surface**
  (per-column max y), **bottom surface** (per-column min y) or the **full scatter
  distribution** of that material; column resolution (bin count) and extraction
  x-range adjustable; multi-line with per-line material/mode/label/color/linestyle
  (defaults: Topography = air bottom, Sed base = sediment bottom, Moho = mantle top)
- **Stress field panel**: σxx/σyy/σxy on element centers (projStressTensor + mesh
  en_map), diverging RdBu colormap with symmetric vmin/vmax
- **Value-range filtering on any field** (like the material threshold extraction):
  field / stress / field-overlay panels accept a display range (a,b); values outside
  the interval are left blank. Scatter overlays accept two-sided value & y thresholds.
- **Fixed-value contours on any field**: field panels and contour overlays accept an
  explicit level list (e.g. `473,673,873`) drawn across the whole coordinate range
  (also works on element-centered fields like projStressTensor).
- **Overlays** (any combination, auto-detected when present):
  - Contours of any mesh field (temperature by default; ℃/K labels, label region picker)
  - Plastic strain threshold scatter (e.g. ≥1.5 & y<4)
  - Velocity vectors (quiver: stride / color / scale / reference arrow)
  - Passive tracers (`gridN-*.h5`, multi-file, multi-color)
  - Field overlay (e.g. viscosity log10, semi-transparent)
- One-click **Full overlay** material panel; multi-step 2×2 / N×1 grid
- Field / swarm / curve base templates

### 🎨 Everything editable — no code
- **Resizable side bars** (ParaView/Inkscape-style drag splitters, double-click to reset, persisted)
- **Live layout readout**: Rows/Cols show the effective auto grid in grey; type to take over, clear to restore auto
- **Unified aspect ratio** at canvas level (per-panel override on every panel type, incl. stress & interface lines)
- **Outside-bottom legend** auto-placed below the xlabel/ticks zone (never occludes the x-axis); **outside-right legend** auto-avoids the colorbar (moves beside it, or falls back to bottom); **colorbar size/position** adjustable (fraction/pad/location) on field, stress and overlay colorbars
- **Bundled QGIS color library (3600+ ramps)**: default QGIS ramps + full cpt-city gradient archive + curated favorites are exported at build time into `core/data/qgis_colormaps.json` and ship with the app (every install has them); local QGIS profile customs are overlaid at runtime. 'QGIS' optgroup with keyword filter; matplotlib-duplicate names removed
- **Reversed colormap** toggle on field/stress/swarm panels and overlays (any cmap, incl. QGIS ramps)
- **Probe click maps to the correct panel (top-origin pixel convention); **material smoothness**: per-panel sample cap (up to all particles, ParaView-like) + anti-aliased sub-pixel markers; **stress panel** locked to the exact model domain (no autoscale side gaps)
- **Built-in palettes** with live gradients (Qaidam / Earth Structure / Journal / 17+ sequential colormaps)
- **Dial-a-color** native color pickers for single colors (background, contour, grid, vectors)
- **Aspect ratio**: auto / data-equal (e.g. 800km:160km → 5:1 band) / custom numeric
- Grid lines, log axes, spines, vmin/vmax, markers, edge colors, colorbar position/size, curve styles — all in the UI
- **Legend inside or outside the axes** (outside right / outside bottom, within the A4 canvas)
- Journal defaults: Arial 7–9pt, ticks in, thin spines, SVG editable text

### ⚡ Performance
- Preview render 300dpi (sharp on large screens); SVG/PDF/PNG300 generated on demand
- **Fast render mode**: particles → density-grid compositing (~0.2s vs 1.5s)
- **Rust engine (plotkit)**: optional rendering backend built on the pure-Rust
  [plotkit](https://github.com/anonymousAAK/plotrs) library (patched with a `quiver`
  vector-field artist). Full 200k-point material figure at A4 300dpi in ~0.9s vs
  ~2.2s matplotlib. Switch in Canvas settings: `Render engine = Rust plotkit`.
- Render result cache (same spec → instant, auto-invalidated on code changes), subsampling disk cache
- **Auto re-render** on parameter change (~650ms debounce)
- Native macOS window (pywebview/WKWebView), starts in <1s

### 🌐 Bilingual UI
- **中文 / English** toggle in the header (persisted); all UI text, panels, toasts switch instantly

## Quick Start

### macOS App (recommended)
```bash
# Build on Apple Silicon (arm64) — no Python needed on the target Mac
conda activate geopixel && pip install pyinstaller
bash build_macos.sh          # → dist/PlotUWG.app + dist/PlotUWG-<ver>-arm64.dmg
```
Copy the DMG to any Apple Silicon Mac, double-click to install. No Python/dependencies required.

### From source
```bash
# 1) env (h5py/numpy/scipy/matplotlib/fastapi/uvicorn/pywebview)
conda create -n geopixel python=3.14 -y
conda activate geopixel
pip install -r requirements.txt

# 2) run (dev server + browser, or native window)
python server.py --port 8787          # browser mode
python run_app.py                     # native macOS window mode
```

## Usage Flow
1. Click 📂 (native folder picker) or paste a path → model folder
2. Time-step bar appears (real Myr) → pick a step
3. `+ Full overlay` → material + temperature + strain + velocity + tracers (auto)
4. Tune style / aspect / overlays in the right panel (auto re-renders)
5. Export PNG+PDF+SVG

## Requirements
- **Build machine**: macOS (Apple Silicon), Python 3.14 (conda `geopixel`), `pip install -r requirements.txt pyinstaller pywebview`
- **Runtime (App)**: macOS 13+ arm64; model files are read-only; user data stored at `~/Library/Application Support/PlotUWG/`

## Directory Structure
```
h5plot_studio/
├── run_app.py            # native window entry (pywebview)
├── server.py             # dev launcher (uvicorn + browser)
├── app.py                # FastAPI routes
├── build_macos.sh        # PyInstaller + DMG build
├── selftest.py           # end-to-end self-test (20 checks)
├── requirements.txt
├── core/
│   ├── config.py         # A4/journal defaults, palettes, persistence
│   ├── h5inspector.py    # h5 tree / stats / model-dir & time scanning
│   ├── plotters.py       # rendering engine (panels + overlays + fast mode)
│   └── probe.py          # click-to-read values
└── web/
    ├── index.html
    ├── app.js            # UI logic + i18n (zh/en)
    └── style.css         # Apple glassmorphism theme
```

## Self-Test
```bash
# Model test data paths are injected via environment variables (no hardcoded local paths)
PLOTUWG_UW_DIR=/path/to/uw217_model_dir \
PLOTUWG_BD_DIR=/path/to/badlands/tin.time50.hdf5 \
python selftest.py   # inspect / render / layout templates / probe / export
```

## License
Internal research tool. Contact the author for usage/licensing terms.
