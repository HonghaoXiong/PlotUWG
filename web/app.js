/* H5Plot Studio — 前端逻辑 */
"use strict";

/* ============================================================
   国际化：中/英文切换（运行时文本翻译，字典驱动）
   ============================================================ */
const I18N_KEY = "h5touwg_lang";
let LANG = (() => { try { return localStorage.getItem(I18N_KEY) || "zh"; } catch (_) { return "zh"; } })();

const I18N_EN = {
  // 通用
  "自动": "Auto", "数据等比 (x:y 同尺度)": "Equal (x:y same scale)",
  "数据等比 (x:y 同尺度，如 800km:160km → 5:1)": "Equal (x:y same scale, e.g. 800km:160km → 5:1)",
  "自定义…": "Custom...", "自定义数值 (y 相对 x 拉伸倍数)": "Custom value (y stretch vs x)",
  "自定义": "Custom", "自动 (a)(b) 面板标注": "Auto (a)(b) panel labels",
  "SVG 可编辑文本 (svg.fonttype=none)": "Editable SVG text (svg.fonttype=none)",
  // 面板与类型
  "物质场": "Material", "场图": "Field", "粒子图": "Swarm", "曲线": "Curve",
  "搜索": "Search", "场叠加": "Field overlay", "温度等值线": "Temp contours",
  "应变散点": "Strain points", "速度矢量": "Velocity vectors", "追踪点": "Tracers",
  "内置预设": "Presets", "连续色板": "Sequential", "面板": "Panels",
  "画板 (A4)": "Canvas (A4)", "方向": "Orientation", "排版 · 行列": "Layout · Grid",
  "样式（期刊默认 = 你的习惯）": "Style (Journal defaults = your habits)",
  "字体": "Font", "正文字号 pt": "Body size pt", "坐标字号 pt": "Axis label pt",
  "线宽 pt": "Line width pt", "图例字号 pt": "Legend size pt", "tick 方向": "Tick dir",
  "朝内": "In", "朝外": "Out",
  "行数 rows": "Rows", "列数 cols": "Cols",
  "绘图配置": "Plot Config", "渲染中…": "Rendering...",
  "请先添加至少一个面板（或在检视器里点「发送到绘图」）": "Add at least one panel first",
  "请先渲染一次": "Render first", "该 dataset 暂不识别为可直接绘图（请手动添加面板）": "Dataset not directly plottable (use manual add)",
  "没有有效 step": "No valid step", "选择失败: ": "Select failed: ",
  "浏览器模式：请在地址栏输入路径（App 版本可用原生选择器）": "Browser mode: type the path (native picker in the App)",
  "输入多个 step，如 50,150,200,250；会按当前行列布局排版": "Multiple steps, e.g. 50,150,200,250",
  "材质 + 温度等值线 + 应变散点 + 速度矢量 + 追踪点（存在即叠加）": "Material + temp contours + strain + velocity + tracers (auto)",
  // 检视器
  "在左侧选择 .h5 / .hdf5 文件查看结构与内容": "Select an .h5 / .hdf5 file on the left",
  "点击 dataset 可查看元信息、采样预览，并一键发送到绘图工坊": "Click a dataset for metadata, preview, and send to the plot studio",
  "在检视器中点\"发送到绘图\"，或到右侧手动添加面板后点\"渲染\"": "Click \"Send to Plot\" in the inspector, or add panels on the right",
  "也可以在左侧选好时间步后点「＋ 物质场图 / 综合物质场图」": "Or pick a time step and use Material / Full-overlay buttons",
  "表头预览（前 ": "Header preview (first ", " 行）": " rows)", "类型": "Type",
  "大小": "Size", "压缩": "Compression", "chunks": "chunks", "数值统计（采样）": "Stats (sampled)",
  "属性 attrs": "Attributes", "发送到 A4 绘图工坊": "Send to A4 Plot Studio", "已打开 ": "Opened ",
  "当前文件类型：": "File type: ", " · 关联 ": " · XMF: ",
  "点击左侧 dataset 查看详情或发送到绘图。": "Click a dataset on the left for details or send to plot.",
  "（空目录或没有 h5 文件）": "(empty or no h5 files)", "最近：": "Recent: ",
  "（无）": "(none)", "字段: ": "Fields: ",
  // 时间步条与按钮
  "🗂 模型目录 · 时间自动对齐": "Model dir · time auto-align",
  "＋ 物质场图 (Qaidam)": "+ Material (Qaidam)", "＋ 综合物质场图 (全叠加)": "+ Full overlay",
  "＋ 多时间步四连图…": "+ Multi-step grid...",
  // 面板卡片
  "快速渲染（粒子→网格，约 10x 快，出图时建议关）": "Fast render (particles→grid, ~10x faster)",
  "材料图例": "Material legend", "材料配色": "Material palette", "背景色": "Background",
  "只画材料 id（逗号分隔，留空=全部）": "Material ids only (comma, empty=all)",
  "marker 大小": "Marker size", "图例位置": "Legend loc", "图例": "Legend",
  "横纵比": "Aspect ratio", "坐标/标签/高级": "Coords/Labels/Advanced", "更多选项": "More options",
  "网格线": "Grid", "网格样式": "Grid style", "网格颜色": "Grid color",
  "x 轴 log": "x log", "y 轴 log": "y log", "显示上/右边框": "Show top/right spines",
  "vmin": "vmin", "vmax": "vmax", "marker 形状": "Marker", "边缘色（none=无）": "Edge (none)",
  "colorbar 位置": "Colorbar loc", "cb fraction": "cb fraction", "cb pad": "cb pad",
  "线型": "Line style", "线宽": "Line width", "xlabel": "xlabel", "ylabel": "ylabel",
  "文件": "File", "dataset": "dataset", "列（逗号分隔）": "Columns (comma)",
  "值阈值 (≥)": "Value ≥", "y 上限 (<)": "y <", "levels (K,逗号)": "levels (K,comma)",
  "颜色": "Color", "颜色 (hex 或 speed)": "Color (hex or speed)",
  "颜色 (逗号分隔)": "Colors (comma)", "标签 (逗号分隔)": "Labels (comma)",
  "文件 (逗号分隔多个)": "Files (comma)", "stride (隔 n 点画一箭头)": "stride",
  "scale": "scale", "width": "width", "key_uv (参考箭头)": "key_uv", "key_text": "key_text",
  "cmap": "colormap", "alpha": "alpha", "size": "size", "colorbar": "colorbar",
  "标注温度": "Label temps", "log10": "log10", "参数": "Params", "删除": "Delete",
  "位置": "pos", "面板 ": "Panel ", "·（位置": "· (pos ", "）。": ")",
  // 图例位置
  "best": "best", "lower center": "lower center", "lower left": "lower left",
  "lower right": "lower right", "upper left": "upper left", "upper right": "upper right",
  "outside right": "outside right", "outside bottom": "outside bottom",
  // marker 形状
  "o 圆点": "o circle", "s 方块": "s square", "^ 三角": "^ triangle",
  "D 菱形": "D diamond", "x 叉": "x cross", "+ 加号": "+ plus", "* 星": "* star", ".": ".",
  // 线型与风格
  "实线": "solid", "虚线": "dashed", "点线": "dotted", "点划 -.": "dash-dot",
  "实线 -": "solid -", "虚线 --": "dashed --", "点线 :": "dotted :",
  // toast / 提示
  "已添加": "Added", "已导出 → ": "Exported → ", "导出失败: ": "Export failed: ",
  "探针失败: ": "Probe failed: ", "渲染失败": "Render failed", "JS 错误: ": "JS error: ",
  "路径不存在或不是目录": "Path does not exist or is not a directory",
  "文件不存在: ": "File not found: ", "不是 h5/hdf5 文件: ": "Not an h5/hdf5 file: ",
  "读取失败: ": "Read failed: ", "绘图失败: ": "Plot failed: ",
  "渲染产物不存在": "Rendered asset not found", "导出目标不是目录": "Export target is not a directory",
  "无法创建导出目录: ": "Cannot create export dir: ", "高分辨率产物生成失败": "Hi-res asset failed",
  "顶点": "Vertex", "点": "point", "个": " items", "K": "K", "km": "km",
  "输入目录路径…": "Enter directory path...", "输入目录路径或选择下方目录…": "Enter path...",
  "如需输入路径…": "Enter path...",
  // 标题与杂项
  "◫ 导出 PNG+PDF+SVG": "⬇ Export PNG+PDF+SVG", "◫ 渲染 (A4)": "⛶ Render (A4)",
  "▦ H5 检视": "▦ Inspect", "◫ A4 画布": "⛶ A4 Canvas",
  "◫ A4 画布": "⛶ A4 Canvas",
  "● 服务正常": "● Server OK", "✕ 服务异常": "✕ Server error",
  "导出目录（留空 = 图片文件所在目录）": "Export dir (empty = figure's folder)",
  "留空=自动。想要物理等比（如 x 800km : y 160km → 5:1 横条）：在面板「横纵比」里选\"数据等比\"。":
    "Empty = auto. For physical aspect (e.g. 800km:160km = 5:1 band) choose \"Equal\" in the panel.",
  "🔄": "🔄",
};

function tr(s) {
  if (!s) return s;
  if (LANG === "en") return I18N_EN[s] || s;
  return s;
}

/* 文本节点 + placeholder 翻译（递归）：中文边界正则替换（可处理复合文本） */
let _I18N_PAIRS = null;
function _i18nPairs() {
  if (_I18N_PAIRS) return _I18N_PAIRS;
  _I18N_PAIRS = Object.entries(I18N_EN).sort((a, b) => b[0].length - a[0].length);
  return _I18N_PAIRS;
}
function localizeNode(root) {
  if (!root || LANG !== "en") return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => {
      const t = n.nodeValue;
      return (t && /[\u4e00-\u9fff]/.test(t))
        ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    },
  });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const n of nodes) {
    if (n.parentElement && n.parentElement.closest("script,style,code")) continue;
    let v = n.nodeValue;
    let changed = false;
    for (const [zh, en] of _i18nPairs()) {
      try {
        const esc = zh.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const re = new RegExp(`(?<![\u4e00-\u9fff])${esc}(?![\u4e00-\u9fff])`, "g");
        if (re.test(v)) { v = v.replace(re, en); changed = true; }
      } catch (_) { /* skip */ }
    }
    if (changed) n.nodeValue = v;
  }
  root.querySelectorAll("[placeholder]").forEach((el) => {
    const p = el.getAttribute("placeholder");
    if (p && I18N_EN[p]) el.setAttribute("placeholder", I18N_EN[p]);
  });
}

/* 动态内容翻译（MutationObserver：innerHTML 插入后自动翻译） */
let _i18nObs = null;
function initI18n() {
  if (_i18nObs || LANG !== "en") return;
  _i18nObs = new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type === "childList") {
        for (const n of m.addedNodes) {
          if (n.nodeType === 1) localizeNode(n);
        }
      }
    }
  });
  _i18nObs.observe(document.body, { childList: true, subtree: true });
}

function setLang(lang) {
  try { localStorage.setItem(I18N_KEY, lang); } catch (_) {}
  location.reload();
}


const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const state = {
  currentDir: "",
  fileInfo: null,        // 当前打开的 h5 文件信息（检视器）
  panels: [],            // 绘图面板列表
  plotMeta: null,        // 最近一次渲染元信息
  config: null,
  modelScan: null,       // 当前目录的模型时间步扫描结果
  probeTimer: null,
  homeDir: "",           // 家目录（打包后不写死本机路径）
  cmapColors: {},        // /api/cmaps 色板采样色值（名称→色值数组，用于预览条）
};

/* ---------------- API ---------------- */
async function api(path, body, method = "POST") {
  const isGet = String(method || "POST").toUpperCase() === "GET";
  const res = await fetch(path, {
    method,
    headers: isGet ? undefined : { "Content-Type": "application/json" },
    body: isGet ? undefined : (body ? JSON.stringify(body) : undefined),
  });
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = j.detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

function toast(msg, isErr = false) {
  const t = $("#toast");
  t.textContent = tr(String(msg));
  t.style.display = "block";
  t.style.background = isErr ? "rgba(178,34,34,.93)" : "rgba(31,36,48,.92)";
  clearTimeout(state.probeTimer);
  state.probeTimer = setTimeout(() => (t.style.display = "none"), 3600);
}

function fmtBytes(b) {
  if (b == null) return "";
  if (b < 1024) return b + " B";
  if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
  return (b / 1048576).toFixed(1) + " MB";
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* ---------------- 启动 ---------------- */
async function boot() {
  window.addEventListener("error", (e) => {
    const t = $("#toast"); t.textContent = "JS 错误: " + (e.message || e);
    t.style.display = "block";
  });
  try { await api("/api/health", {}, "GET"); $("#srv-status").textContent = "● 服务正常"; }
  catch (e) { $("#srv-status").textContent = "✕ 服务异常"; }
  try { state.config = await api("/api/config", {}, "GET"); applyConfigToUI(state.config); } catch (_) {}
  loadPanels();
  try { const h = await api("/api/home", {}, "GET"); state.homeDir = h.path || ""; } catch (_) { state.homeDir = ""; }
  try { const c = await api("/api/cmaps", {}, "GET"); state.cmapColors = c.cmaps || {}; } catch (_) { state.cmapColors = {}; }
  renderCmapPreviews();
  const recent = await api("/api/recent", {}, "GET").catch(() => ({ paths: [] }));
  renderRecent(recent.paths || []);
  // 只取目录作为默认浏览起点（最近路径里可能有 h5 文件）
  const isH5 = (p) => /\.(h5|hdf5|hdf)$/i.test(p);
  const firstDir = (recent.paths || []).find((p) => !isH5(p));
  const start = firstDir || (state.homeDir || "~");
  $("#path-input").value = start;
  browseDir(start);
  bindEvents();
  // 国际化：静态文本翻译 + 动态内容观察
  if (LANG === "en") localizeNode(document.body);
  initI18n();
  const langBtn = document.getElementById("lang-toggle");
  if (langBtn) {
    langBtn.textContent = LANG === "en" ? "中文" : "EN";
    langBtn.onclick = () => setLang(LANG === "en" ? "zh" : "en");
  }
}

function bindEvents() {
  $("#path-go").onclick = () => browseDir($("#path-input").value.trim());
  // 原生文件夹/文件选择器（pywebview App 内弹出 macOS 对话框）
  $("#path-pick").onclick = async () => {
    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.choose_folder) {
        const dir = await window.pywebview.api.choose_folder();
        if (dir) { $("#path-input").value = dir; browseDir(dir); return; }
      }
      if (window.pywebview && window.pywebview.api && window.pywebview.api.choose_file) {
        const file = await window.pywebview.api.choose_file();
        if (file) { openH5(file); return; }
      }
      toast("浏览器模式：请在地址栏输入路径（App 版本可用原生选择器）", true);
    } catch (e) { toast("选择失败: " + (e.message || e), true); }
  };
  $("#path-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") browseDir($("#path-input").value.trim());
  });
  $("#path-home").onclick = () => { const h = state.homeDir || "~"; $("#path-input").value = h; browseDir(h); };
  $("#path-up").onclick = () => {
    const p = state.currentDir;
    const up = p.replace(/\/[^/]+$/, "").replace(/\/+$/, "") || "/";
    $("#path-input").value = up; browseDir(up);
  };
  $("#tab-inspect").onclick = () => switchTab("inspect");
  $("#tab-plot").onclick = () => switchTab("plot");

  // 窄屏配置抽屉开关
  $("#cfg-toggle").onclick = () => toggleConfig(true);
  $("#cfg-mask").onclick = () => toggleConfig(false);
  $("#cfg-close").onclick = () => toggleConfig(false);

  // 绘图
  $("#render-btn").onclick = renderPlot;
  $("#export-btn").onclick = exportPlot;
  $("#add-field").onclick = () => addPanel({ kind: "field" });
  $("#add-swarm").onclick = () => addPanel({ kind: "swarm" });
  $("#add-curve").onclick = () => addPanel({ kind: "curve" });
  $("#plot-img").addEventListener("click", onPlotClick);
  $("#plot-img").addEventListener("mousemove", (e) => moveTip(e));
  $("#plot-img").addEventListener("mouseleave", () => $("#probe-tip").style.display = "none");

  // 配置变化即时保存
  ["cfg-font", "cfg-font-size", "cfg-label-size", "cfg-linewidth",
   "cfg-legend-size", "cfg-tick-dir", "cfg-orientation", "cfg-svgtext",
   "cfg-panel-labels", "cfg-rows", "cfg-cols"].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("change", () => { saveConfigSilent(); scheduleAutoRender(); });
  });
}

function switchTab(name) {
  $$("#center-tabs .ctab").forEach((b) => b.classList.remove("active"));
  $(`#tab-${name}`).classList.add("active");
  $$(".cview").forEach((v) => v.classList.remove("active"));
  $(`#view-${name}`).classList.add("active");
}

function toggleConfig(open) {
  const cfg = $("#plot-config");
  const mask = $("#cfg-mask");
  if (!cfg) return;
  if (open === undefined) open = !cfg.classList.contains("open");
  cfg.classList.toggle("open", open);
  if (mask) mask.classList.toggle("show", open);
}

/* ---------------- 目录浏览 ---------------- */
async function browseDir(path) {
  if (!path) return;
  try {
    const out = await api("/api/dirs", { path, kind: "dir" });
    state.currentDir = out.path;
    $("#path-input").value = out.path;
    if (out.error) { toast(out.error, true); return; }
    renderDir(out);
    scanStep(out.path);
  } catch (e) { toast(String(e.message || e), true); }
}

/* ---- 模型时间步扫描（swarm/materialField/温度等自动对齐） ---- */
async function scanStep(path) {
  const bar = $("#step-bar");
  try {
    const scan = await api("/api/step-scan", { path, kind: "dir" });
    state.modelScan = scan;
    if (!scan.is_model_dir) { bar.classList.add("hidden"); return; }
    renderStepBar(scan);
  } catch (_) { bar.classList.add("hidden"); }
}

function renderStepBar(scan) {
  const bar = $("#step-bar");
  bar.innerHTML = "";
  bar.classList.remove("hidden");
  const dir = scan.path.replace(/\/$/, "");
  const steps = scan.steps || [];
  const mid = steps[Math.floor(steps.length / 2)] ?? (steps[steps.length - 1] ?? 0);
  const sel = document.createElement("select");
  sel.id = "step-select";
  steps.forEach((s) => {
    const o = document.createElement("option");
    o.value = s;
    let tMyr;
    if (scan.time_scale_myr && scan.time_start != null && scan.time_end != null
        && scan.step_start != null && scan.step_end != null && scan.step_end !== scan.step_start) {
      // 真实时间（timeField 线性插值，单位年 → Myr）
      const t = scan.time_start + (scan.time_end - scan.time_start) * (s - scan.step_start) / (scan.step_end - scan.step_start);
      tMyr = t / scan.time_scale_myr;
    } else {
      tMyr = s / 10;   // 兜底：step/10 Myr（用户模型惯例）
    }
    o.text = `step ${s}  (${tMyr.toFixed(1)} Myr)`;
    if (s === mid) o.selected = true;
    sel.appendChild(o);
  });
  const f = scan.fields || {};
  const fieldList = Object.keys(f).filter((k) => /^(swarm|materialField|temperature|plasticStrain|projViscosityField|velocityField)/.test(k));
  const hint = document.createElement("div");
  hint.className = "sb-hint";
  hint.textContent = "字段: " + (fieldList.map((k) => k).join(" · ") || "");
  const row = document.createElement("div");
  row.className = "sb-row";
  const title = document.createElement("div");
  title.className = "sb-title";
  title.textContent = "🗂 模型目录 · 时间自动对齐";
  const btn = document.createElement("button");
  btn.className = "sb-btn";
  btn.textContent = "＋ 物质场图 (Qaidam)";
  btn.onclick = () => generateMaterialPanel(parseInt(sel.value, 10), dir, scan);
  const btnFull = document.createElement("button");
  btnFull.className = "sb-btn sb-btn-alt";
  btnFull.textContent = "＋ 综合物质场图 (全叠加)";
  btnFull.title = "材质 + 温度等值线 + 应变散点 + 速度矢量 + 追踪点（存在即叠加）";
  btnFull.onclick = () => generateFullMaterialPanel(parseInt(sel.value, 10), dir, scan);
  const btnM = document.createElement("button");
  btnM.className = "sb-btn sb-btn-orange";
  btnM.textContent = "＋ 多时间步四连图…";
  btnM.title = "输入多个 step，如 50,150,200,250；会按当前行列布局排版";
  btnM.onclick = () => addMaterialPanelsForSteps(dir, scan);
  row.appendChild(sel);
  row.appendChild(btn);
  row.appendChild(btnFull);
  row.appendChild(btnM);
  bar.appendChild(title);
  bar.appendChild(row);
  bar.appendChild(hint);
}

function stepFile(dir, name, step) {
  return `${dir}/${name}-${step}.h5`;
}

function buildMaterialPanel(step, dir, scan, mode = "default") {
  const f = scan.fields || {};
  const has = (k) => !!f[k];
  const dir2 = dir.replace(/\/$/, "");
  const panel = {
    kind: "material",
    step_dir: dir2,
    step,
    file: stepFile(dir2, "swarm", step),
    dataset: "data",
    material_file: stepFile(dir2, "materialField", step),
    cmap_preset: "Qaidam",
    bg_color: "#404040",
    marker_size: 1,
    legend: true,
    legend_loc: "lower center",
    xlim: [], ylim: [],
    xlabel: "x [km]", ylabel: "y [km]",
    overlays: [],
  };
  if (mode === "base") return panel;
  // 默认叠加：温度等值线（若有）+ 应变散点（若有）——沿用你的常规组合
  if (has("temperature") && (mode === "default" || mode === "full")) {
    panel.overlays.push({
      type: "contour", ov_type: "temperature",
      file: stepFile(dir2, "temperature", step),
      dataset: "data",
      levels: [473, 673, 873, 1073, 1273, 1473],
      color: "#ff557f", clabel: true,
      mesh_file: dir2 + "/mesh.h5",
      label_region: { x0: 205, x1: 595, y0: -98, y1: 0 },
    });
  }
  if (has("plasticStrain") && (mode === "default" || mode === "full")) {
    panel.overlays.push({
      type: "scatter", ov_type: "plasticStrain",
      file: stepFile(dir2, "plasticStrain", step),
      dataset: "data",
      cmap: "hot_r", vmin: 1.5, vmax: 4.5, alpha: 0.9, size: 1,
      mask_value: { ge: 1.5 }, mask_y: { lt: 4 },
      colorbar: false, cbar_label: "Plastic strain",
    });
  }
  if (mode === "full") {
    // 速度矢量叠加（若 velocityField 存在）
    const velKey = has("velocityField") ? "velocityField" : (has("projVelocityField") ? "projVelocityField" : null);
    if (velKey && f[velKey].steps.includes(step)) {
      panel.overlays.push({
        type: "vectors", ov_type: "velocity",
        file: stepFile(dir2, velKey, step),
        dataset: "data", ux_col: 0, uy_col: 1,
        mesh_file: dir2 + "/mesh.h5",
        color: "#000000", width: 0.005, alpha: 0.9,
      });
    }
    // 追踪点叠加（gridN 系列，自动找当前 step 的追踪文件）
    const tg = scan.tracer_groups || [];
    if (tg.length) {
      const files = [];
      const labels = [];
      for (const g of tg) {
        if (g.steps.includes(step)) {
          files.push(stepFile(dir2, g.prefix, step));
          labels.push(g.prefix);
        }
      }
      if (files.length) {
        panel.overlays.push({
          type: "tracers", ov_type: "tracers",
          file: files[0], files, labels,
          dataset: "data", color: "#FFD700",
          colors: ["#FFD700", "#00E5FF", "#FF6B6B", "#4ADE80", "#FF9F43", "#C39BD3"],
          marker: "o", size: 5, alpha: 0.95,
          legend: files.length > 1, legend_loc: "lower left",
        });
      }
    }
  }
  return panel;
}

function generateMaterialPanel(step, dir, scan) {
  const panel = buildMaterialPanel(step, dir, scan, "default");
  addPanel(panel);
  switchTab("plot");
  toast(`已添加物质场面板 step=${step}（材质 + 温度等值线 + 应变）`);
}

function generateFullMaterialPanel(step, dir, scan) {
  const panel = buildMaterialPanel(step, dir, scan, "full");
  const nOv = panel.overlays.length;
  addPanel(panel);
  switchTab("plot");
  toast(`已添加综合物质场面板 step=${step}（${nOv} 个叠加：温度/应变/速度/追踪点）`);
}

function addMaterialPanelsForSteps(dir, scan) {
  const input = prompt("输入要绘制的时间步（逗号或空格分隔，自动换算 Myr 显示）：\n例如  50,150,200,250   →  5 / 15 / 20 / 25 Myr\n留空=每隔 50 选出 4 个", "50,150,200,250");
  if (input === null) return;
  const steps = (input.trim().split(/[,\s]+/).map((s) => parseInt(s, 10)))
    .filter((s) => !isNaN(s));
  if (!steps.length) { toast("没有有效 step", true); return; }
  const avail = new Set((scan.steps || []).map((s) => Number(s)));
  const missing = steps.filter((s) => !avail.has(s));
  if (missing.length) {
    toast(`这些 step 不存在: ${missing.join(", ")}`, true);
    return;
  }
  steps.forEach((s) => addPanel(buildMaterialPanel(s, dir, scan)));
  switchTab("plot");
  toast(`已添加 ${steps.length} 个物质场面板 (${steps.map((s) => s / 10).join(", ")} Myr)；在右侧设行列 2×2/4×1 排版`);
}

function renderDir(out) {
  const el = $("#dir-list");
  el.innerHTML = "";
  const items = out.items || [];
  let nShown = 0;
  for (const it of items) {
    if (it.group) {
      const g = document.createElement("div");
      g.className = "grp";
      const head = document.createElement("div");
      head.className = "grp-head";
      head.innerHTML = `<span class="caret">▸</span><span>🗂</span><span class="nm">${esc(it.name)}</span>` +
        `<span class="sz">${it.count} · ${fmtBytes(it.bytes)}</span>`;
      head.title = it.path ?? "";
      const body = document.createElement("div");
      body.className = "grp-body hidden";
      for (const c of it.children || []) {
        const d = document.createElement("div");
        d.className = "dir-item h5";
        d.textContent = c.name;
        if (c.bytes != null) {
          const sz = document.createElement("span");
          sz.className = "sz"; sz.textContent = fmtBytes(c.bytes);
          d.appendChild(sz);
        }
        d.title = c.path;
        d.onclick = () => openH5(c.path);
        body.appendChild(d);
      }
      head.onclick = () => {
        head.querySelector(".caret").textContent = body.classList.contains("hidden") ? "▾" : "▸";
        body.classList.toggle("hidden");
      };
      g.appendChild(head);
      g.appendChild(body);
      el.appendChild(g);
      continue;
    }
    if (!it.is_dir && !it.is_h5) continue;
    nShown++;
    const d = document.createElement("div");
    d.className = "dir-item " + (it.is_dir ? "dir" : "h5");
    if (!it.is_dir) d.classList.add("h5");
    d.textContent = it.name;
    if (!it.is_dir && it.bytes != null) {
      const sz = document.createElement("span");
      sz.className = "sz"; sz.textContent = fmtBytes(it.bytes);
      d.appendChild(sz);
    }
    d.title = it.path;
    d.onclick = () => {
      if (it.is_dir) { $("#path-input").value = it.path; browseDir(it.path); }
      else openH5(it.path);
    };
    el.appendChild(d);
  }
  if (!items.length) el.innerHTML = '<div class="placeholder" style="margin-top:20px">（空目录或没有 h5 文件）</div>';
}

function renderRecent(paths) {
  const el = $("#recent");
  el.innerHTML = "<b>最近：</b>";
  if (!paths || !paths.length) { el.innerHTML = "<b>最近：</b>（无）"; return; }
  for (const p of paths.slice(0, 5)) {
    const s = document.createElement("span");
    s.className = "rp"; s.textContent = p.replace(/^.*\//, "") + " ";
    s.title = p;
    s.onclick = () => { p.endsWith(".h5") || p.endsWith(".hdf5") || p.endsWith(".hdf") ? openH5(p) : browseDir(p); };
    el.appendChild(s);
  }
}

/* ---------------- h5 检视 ---------------- */
async function openH5(path) {
  try {
    const info = await api("/api/open-file", { path, kind: "file" });
    state.fileInfo = info;
    switchTab("inspect");
    $("#path-input").value = path;
    renderH5Meta(info);
    renderH5Tree(info.tree || [], $("#h5-tree"));
    const place = $("#ds-detail");
    place.innerHTML = `<div class="placeholder">已打开 <b>${esc(info.filename)}</b><br>
      当前文件类型：${esc(info.type)}${info.xmf_sibling ? ` · 关联 ${esc(info.xmf_sibling)}` : ""}<br>
      点击左侧 dataset 查看详情或发送到绘图。</div>`;
    renderRecent(undefined);
  } catch (e) { toast(String(e.message || e), true); }
}

function renderH5Meta(info) {
  const el = $("#h5-meta");
  let html = `<b>${esc(info.filename)}</b>  <span style="color:var(--muted)">${fmtBytes(info.size_bytes)} · 类型 ${esc(info.type)}</span>`;
  if (info.xmf_sibling) html += ` <span style="color:var(--accent2)">· XMF: ${esc(info.xmf_sibling)}</span>`;
  if (info.root_attrs && Object.keys(info.root_attrs).length) {
    html += '<div class="attrs">' + Object.entries(info.root_attrs)
      .map(([k, v]) => `<code>${esc(k)}</code> = ${esc(JSON.stringify(v))}`).join(" · ") + "</div>";
  }
  el.innerHTML = html;
}

function renderH5Tree(nodes, container, depth = 0) {
  container.innerHTML = "";
  for (const node of nodes) {
    const li = document.createElement("li");
    if (node.kind === "group") {
      const div = document.createElement("div");
      div.className = "tnode g";
      div.innerHTML = `<span class="nm">${esc(node.name)}/</span>`;
      const childUl = document.createElement("ul");
      childUl.style.display = "none";
      if (node.children && node.children.length) renderH5Tree(node.children, childUl, depth + 1);
      div.onclick = () => {
        div.classList.toggle("open");
        childUl.style.display = childUl.style.display === "none" ? "" : "none";
      };
      li.appendChild(div);
      li.appendChild(childUl);
    } else if (node.kind === "dataset") {
      const div = document.createElement("div");
      div.className = "tnode d";
      div.innerHTML = `<span class="nm">${esc(node.name)}</span><span class="sh">${esc(node.shape)} · ${esc(node.dtype)}</span>` +
        `<span class="send" title="发送到 A4 绘图工坊">→ 绘图</span>`;
      div.onclick = () => showDatasetDetail(node);
      div.querySelector(".send").onclick = (e) => {
        e.stopPropagation();
        sendDatasetToPlot(node);
      };
      li.appendChild(div);
    }
    container.appendChild(li);
  }
}

function showDatasetDetail(node) {
  const el = $("#ds-detail");
  let html = `<h3>${esc(node.path || node.name)}</h3>`;
  html += `<div class="kv">
    <div class="k">类型</div><div>dataset · ${esc(node.dtype)}</div>
    <div class="k">shape</div><div>${esc(node.shape)}</div>
    <div class="k">大小</div><div>${fmtBytes(node.bytes)}</div>
    ${node.compression ? `<div class="k">压缩</div><div>${esc(node.compression)}</div>` : ""}
    ${node.chunks ? `<div class="k">chunks</div><div>${esc(node.chunks)}</div>` : ""}
  </div>`;
  html += `<button class="send-btn" id="detail-send">＋ 发送到 A4 绘图工坊</button>`;
  if (node.stats && Object.keys(node.stats).length) {
    html += `<h3>数值统计（采样）</h3><div class="kv">` +
      Object.entries(node.stats).map(([k, v]) => `<div class="k">${esc(k)}</div><div>${esc(v)}</div>`).join("") +
      `</div>`;
  }
  if (Object.keys(node.attrs || {}).length) {
    html += `<h3>属性 attrs</h3><div class="attrs">` +
      Object.entries(node.attrs).map(([k, v]) => `<code>${esc(k)}</code> = ${esc(JSON.stringify(v))}`).join("<br>") +
      `</div>`;
  }
  if (node.head && node.head.length) {
    const arr = typeof node.head[0] === "object" && !Array.isArray(node.head[0]) && node.head[0].error
      ? null : node.head;
    if (arr) {
      html += `<h3>表头预览（前 ${arr.length} 行）</h3><table class="head"><tr>` +
        arr.map((row) => {
          const colss = Array.isArray(row) ? row : [row];
          return "<tr>" + colss.map((c) => `<td>${esc(c)}</td>`).join("") + "</tr>";
        }).join("") + "</table>";
    }
  }
  el.innerHTML = html;
  document.getElementById("detail-send").onclick = () => sendDatasetToPlot(node);
}

/* ---------------- 发送到绘图 / 面板管理 ---------------- */
function suggestPanel(node) {
  const info = state.fileInfo;
  const file = info.path;
  const fileName = info.filename;
  const name = node.name;
  const kindOf = info.type;
  const base = {
    file,
    dataset: node.name,
    label: "",
    title: name,
    xlim: [], ylim: [],
  };
  let panel = null;
  const num1d = node.ndim === 1 && node.dtype && /^(float|int)/.test(node.dtype);

  if (kindOf === "badlands" && node.shape_raw && node.shape_raw[1] === 3) {
    // Badlands coords 或同类数组 → 2D 垂直剖面/平面映射用 scatter（z 着色）
    panel = { ...base, kind: "swarm", x_col: 0, y_col: 1, color_by: "column",
              color_column: Math.min(2, node.shape_raw[1] - 1), cmap: "turbo",
              marker_size: 1, alpha: 1, legend: false };
  } else if (kindOf === "swarm" || /^swarm/.test(name)) {
    panel = { ...base, kind: "swarm", x_col: 0, y_col: 1, color_by: "material",
              marker_size: 1, alpha: 1, legend: true };
    const pres = info.path.replace(/[^/]+$/, "");
    panel.material_file = pres + "materialField" + (fileName.match(/swarm-(\d+)/)?.[1] ? "-" + fileName.match(/swarm-(\d+)/)[1] : "") + ".h5";
  } else if (kindOf === "field" && num1d || (kindOf === "field" && node.ndim === 2 && node.dtype && /^(float|int)/.test(node.dtype))) {
    panel = { ...base, kind: "field", column: 0, cmap: "turbo", colorbar: true,
              contour: false, mesh_file: (info.path.replace(/[^/]+$/, "") + "mesh.h5") };
    // 带 -step 后缀的场文件匹配同名 step 的 mesh?
    const probe = info.path; // 同目录 mesh.h5
  } else if (num1d) {
    panel = { ...base, kind: "curve", columns: [0], legend: true,
              style_conf: { colors: ["#2878B5", "#D97924", "#2CA02C", "#D7191C", "#444444"], lw: 1.2 } };
  } else {
    toast("该 dataset 暂不识别为可直接绘图（请手动添加面板）", true);
    return;
  }
  addPanel(panel);
  switchTab("plot");
  toast(`已添加 ${panel.kind} 面板，点「渲染」出图`);
}

function sendDatasetToPlot(node) { suggestPanel(node); }

function addPanel(panel) {
  if (!panel) panel = { kind: "field", file: state.fileInfo?.path || "", dataset: "data",
                        column: 0, cmap: "turbo", colorbar: true, contour: false, label: "" };
  if (!panel.file && state.fileInfo) panel.file = state.fileInfo.path;
  if (!panel.dataset) panel.dataset = "data";
  if (!panel.cmap) panel.cmap = "turbo";
  state.panels.push(panel);
  renderPanels();
  savePanels();
}

function removePanel(i) {
  state.panels.splice(i, 1);
  renderPanels();
  savePanels();
}

/* ---- 面板持久化（localStorage）：刷新/重启后自动恢复画布 ---- */
const PANELS_KEY = "h5plot_studio_panels_v1";
function savePanels() {
  try {
    localStorage.setItem(PANELS_KEY, JSON.stringify(state.panels));
  } catch (_) { /* 超限时忽略 */ }
}
function loadPanels() {
  try {
    const raw = localStorage.getItem(PANELS_KEY);
    if (!raw) return;
    const arr = JSON.parse(raw);
    if (Array.isArray(arr) && arr.length) {
      state.panels = arr;
      renderPanels();
    }
  } catch (_) { /* 忽略损坏缓存 */ }
}

function renderCmapPreviews() {
  // 更新所有已渲染的色板预览条（boot 拉取 /api/cmaps 后调用）
  $$(".cmap-row2").forEach((row) => {
    const sel = row.querySelector("select");
    if (!sel) return;
    const prev = row.querySelector(".cmap-preview");
    if (!prev) return;
    const cs = state.cmapColors[sel.value] || PRESET_CMAPS[sel.value];
    if (cs && cs.length) prev.style.background = "linear-gradient(90deg," + cs.join(",") + ")";
  });
}

function renderPanels() {
  const el = $("#panel-list");
  el.innerHTML = "";
  state.panels.forEach((p, i) => {
    const card = document.createElement("div");
    card.className = "panel-card";
    const tag = { field: "场图", swarm: "粒子图", curve: "曲线", material: "物质场" }[p.kind] || p.kind;
    const dims = currentGridDims();
    const posTag = ` · 位置(${Math.floor(i / Math.max(dims.cols, 1)) + 1},${(i % Math.max(dims.cols, 1)) + 1})`;
    let html = p.kind === "material"
      ? materialCardHTML(p, i)
      : `<h4><span class="tag">${tag}</span> 面板 ${i + 1}${posTag}
       <button class="panel-del" data-i="${i}" title="删除">✕</button></h4>`;
    if (p.kind === "material") {
      // 在标签栏补位置信息（materialCardHTML 内部 handle 标题，这里替换标题行）
    }
    html += `<label class="file-v">文件<small> ${esc(p.file)}</small></label>`;
    html += `<label>dataset
      <input data-f="dataset" data-i="${i}" value="${esc(p.dataset || "")}" placeholder="data"></label>`;
    if (p.kind === "field") {
      html += `
        <label>列<select data-f="column" data-i="${i}"><option value="0">0</option><option value="1">1</option><option value="2">2</option></select></label>
        <label class="cmap-row">色板 <div class="cmap-row2"><select data-f="cmap" data-i="${i}"></select><span class="cmap-preview" id="cmap-prev-p-${i}" style="background:linear-gradient(90deg,#2878B5,#D97924)"></span></div></label>
        <label><input type="checkbox" data-f="colorbar" data-i="${i}" checked> colorbar</label>
        <label><input type="checkbox" data-f="contour" data-i="${i}"> 等值线 contour</label>
        <details><summary>更多选项</summary>
          <label>xlabel <input data-f="xlabel" data-i="${i}" value="${esc(p.xlabel || "")}"></label>
          <label>ylabel <input data-f="ylabel" data-i="${i}" value="${esc(p.ylabel || "")}"></label>
          <label>横纵比 ${aspectHTML(i, p.aspect)}</label>
          <label>xlim (a,b) <input data-f="xlim" data-i="${i}" value="${(p.xlim || []).join(",")}" placeholder="0,800"></label>
          <label>ylim (a,b) <input data-f="ylim" data-i="${i}" value="${(p.ylim || []).join(",")}" placeholder="-160,10"></label>
          ${advancedHTML(i, p, { vmin: true, cb: true })}
        </details>`;
    } else if (p.kind === "swarm") {
      html += `
        <label>x_col <input type="number" data-f="x_col" data-i="${i}" value="${p.x_col ?? 0}"></label>
        <label>y_col <input type="number" data-f="y_col" data-i="${i}" value="${p.y_col ?? 1}"></label>
        <label>着色<select data-f="color_by" data-i="${i}">
          <option value="material" ${p.color_by === "material" ? "selected" : ""}>材料 (materialField)</option>
          <option value="column" ${p.color_by === "column" ? "selected" : ""}>数值列</option>
        </select></label>
        <label id="swarm-col-row-${i}" ${p.color_by !== "column" ? 'class="hidden"' : ""}>数值列号
          <input type="number" data-f="color_column" data-i="${i}" value="${p.color_column ?? 2}"></label>
        <label class="cmap-row">色板 <div class="cmap-row2"><select data-f="cmap" data-i="${i}"></select><span class="cmap-preview" id="cmap-prev-p-${i}" style="background:linear-gradient(90deg,#2878B5,#D97924)"></span></div></label>
        <label><input type="checkbox" data-f="legend" data-i="${i}" ${p.legend === false ? "" : "checked"}> 图例</label>
        <label>图例位置<select data-f="legend_loc" data-i="${i}">
          ${["best","upper left","upper right","lower left","lower right","outside right","outside bottom"].map(l => `<option value="${l}" ${(p.legend_loc || "best") === l ? "selected" : ""}>${l}</option>`).join("")}
        </select></label>
        <details><summary>更多选项</summary>
          <label>xlabel <input data-f="xlabel" data-i="${i}" value="${esc(p.xlabel || "")}"></label>
          <label>ylabel <input data-f="ylabel" data-i="${i}" value="${esc(p.ylabel || "")}"></label>
          <label>横纵比 ${aspectHTML(i, p.aspect)}</label>
          <label>marker 大小 <input type="number" data-f="marker_size" data-i="${i}" value="${p.marker_size ?? 1}" step="0.5"></label>
          <label>xlim (a,b) <input data-f="xlim" data-i="${i}" value="${(p.xlim || []).join(",")}"></label>
          <label>ylim (a,b) <input data-f="ylim" data-i="${i}" value="${(p.ylim || []).join(",")}"></label>
          ${advancedHTML(i, p, { vmin: true, marker: true, cb: true })}
        </details>`;
    } else if (p.kind === "curve") {
      html += `
        <label>列（逗号分隔） <input data-f="columns_str" data-i="${i}" value="${(p.columns || [0]).join(",")}"></label>
        <label><input type="checkbox" data-f="legend" data-i="${i}" ${p.legend === false ? "" : "checked"}> 图例</label>
        <label>图例位置<select data-f="legend_loc" data-i="${i}">
          ${["best","upper left","upper right","lower left","lower right","outside right","outside bottom"].map(l => `<option value="${l}" ${(p.legend_loc || "best") === l ? "selected" : ""}>${l}</option>`).join("")}
        </select></label>
        <details><summary>更多选项</summary>
          <label>xlabel <input data-f="xlabel" data-i="${i}" value="${esc(p.xlabel || "")}"></label>
          <label>ylabel <input data-f="ylabel" data-i="${i}" value="${esc(p.ylabel || "")}"></label>
          <label>线型 <select data-f="line_style" data-i="${i}">
            <option value="">自动</option>
            <option value="-" ${p.line_style === "-" ? "selected" : ""}>实线 -</option>
            <option value="--" ${p.line_style === "--" ? "selected" : ""}>虚线 --</option>
            <option value=":" ${p.line_style === ":" ? "selected" : ""}>点线 :</option>
            <option value="-." ${p.line_style === "-." ? "selected" : ""}>点划 -.</option>
          </select></label>
          <label>线宽 <input type="number" step="0.1" data-f="line_width" data-i="${i}" value="${p.line_width ?? ""}"></label>
          <label>marker <select data-f="marker" data-i="${i}">
            <option value="">无</option>
            ${["o", "s", "^", "D", "x", "+", "*", "."].map(m => `<option value="${m}" ${p.marker === m ? "selected" : ""}>${m}</option>`).join("")}
          </select></label>
          <label>marker 大小 <input type="number" step="0.5" data-f="marker_size" data-i="${i}" value="${p.marker_size ?? ""}"></label>
          <label>xlim (a,b) <input data-f="xlim" data-i="${i}" value="${(p.xlim || []).join(",")}"></label>
          <label>ylim (a,b) <input data-f="ylim" data-i="${i}" value="${(p.ylim || []).join(",")}"></label>
          ${advancedHTML(i, p, {})}
        </details>`;
    }
    card.innerHTML = html;
    el.appendChild(card);
  });
  // 填充色板下拉 + 恢复当前选择
  $$("#panel-list select[data-f=cmap]").forEach((sel) => {
    fillCmapSelect(sel);
    const i = +sel.dataset.i;
    const p = state.panels[i];
    if (p) {
      sel.value = p.cmap || (p.cmap_values ? "Qaidam" :
        (sel.querySelector('option[value="Qaidam"]') ? "Qaidam" : "turbo"));
    }
    renderCmapPreviews();
  });
  // 事件绑定
  $$("#panel-list [data-i]").forEach((inp) => {
    if (inp.classList.contains("panel-del")) { inp.onclick = () => removePanel(+inp.dataset.i); return; }
    if (inp.dataset.act || inp.dataset.ovf) return;    // 由叠加层专属绑定处理
    inp.addEventListener("change", (e) => {
      const i = +e.target.dataset.i, f = e.target.dataset.f;
      const p = state.panels[i];
      if (!p) return;
      let v = e.target.type === "checkbox" ? e.target.checked : e.target.value;
      if (f === "xlim") v = v.split(",").map(Number);
      if (f === "ylim") v = v.split(",").map(Number);
      if (["vmin", "vmax", "cb_fraction", "cb_pad"].includes(f)) v = v === "" ? null : parseFloat(v);
      if (f === "columns_str") p.columns = v.split(",").map(Number);
      if (f === "only_materials") v = v.trim() ? v.split(",").map((s) => parseInt(s.trim(), 10)) : [];
      if (f === "colorbar" || f === "contour" || f === "legend") v = e.target.checked;
      if (f === "columns_str") return;
      if (f === "cmap") {
        // 内置预设 → cmap_values（同时存预设名便于 UI 显示）；连续色板 → cmap 名称
        if (PRESET_CMAPS[v]) { p.cmap_values = PRESET_CMAPS[v]; p.cmap = v; }
        else { p.cmap = v; delete p.cmap_values; }
        const prev = document.getElementById(`cmap-prev-p-${i}`);
        if (prev) { const cs = state.cmapColors[v] || PRESET_CMAPS[v]; if (cs && cs.length) prev.style.background = "linear-gradient(90deg," + cs.join(",") + ")"; }
        return;
      }
      if (f === "fast") { p.fast = e.target.checked; savePanels(); return; }
      if (f === "aspect") {
        const row = document.getElementById(`aspect-num-row-${i}`);
        if (v === "custom") { if (row) row.classList.remove("hidden"); if (p.aspect === undefined || p.aspect === "" || p.aspect === "equal") p.aspect = 1; }
        else { if (row) row.classList.add("hidden"); p.aspect = v || ""; }
        savePanels(); return;
      }
      if (f === "aspect_num") {
        p.aspect = (v === "" || isNaN(parseFloat(v))) ? "" : parseFloat(v);
        savePanels(); return;
      }
      p[f] = v;
      savePanels();
      scheduleAutoRender();
    });
  });
  // aspect 自定义输入行显示恢复
  $$("#panel-list [data-f=aspect]").forEach((sel) => {
    const i = +sel.dataset.i;
    const p = state.panels[i];
    const row = document.getElementById(`aspect-num-row-${i}`);
    if (row && p && typeof p.aspect === "number" && !isNaN(p.aspect)) row.classList.remove("hidden");
  });
  // color_by 联动数值列行
  $$("#panel-list select[data-f=color_by]").forEach((sel) => {
    sel.onchange = () => {
      const i = +sel.dataset.i;
      const row = document.getElementById(`swarm-col-row-${i}`);
      if (row) row.classList.toggle("hidden", sel.value !== "column");
    };
  });
  // 物质场：step 联动（同目录面板同步替换）
  $$("#panel-list [data-f=step]").forEach((inp) => {
    inp.addEventListener("change", (e) => {
      const i = +e.target.dataset.i;
      const step = parseInt(e.target.value, 10);
      if (isNaN(step)) return;
      state.panels.forEach((pp, j) => { if (pp.step_dir) applyStep(pp, step); });
      renderPanels();
      toast(`step 已同步为 ${step}（${step / 10} Myr）`);
    });
  });
  // 物质场：叠加层按钮 / 删除 / 参数
  $$("#panel-list [data-act=ov-add]").forEach((btn) => {
    btn.onclick = () => {
      const i = +btn.dataset.i, ovType = btn.dataset.ov;
      const p = state.panels[i];
      if (!p) return;
      p.overlays = p.overlays || [];
      const d = (p.step_dir || state.currentDir || "").replace(/\/$/, "");
      const st = p.step ?? 0;
      const ov = { type: ovType, ov_type: ovType, file: "", dataset: "data" };
      if (ovType === "contour") {
        ov.file = `${d}/temperature-${st}.h5`; ov.mesh_file = `${d}/mesh.h5`;
        ov.levels = [473, 673, 873, 1073, 1273, 1473]; ov.color = "#ff557f";
        ov.label_region = { x0: 205, x1: 595, y0: -98, y1: 0 };
      } else if (ovType === "scatter") {
        ov.file = `${d}/plasticStrain-${st}.h5`; ov.cmap = "hot_r";
        ov.vmin = 1.5; ov.vmax = 4.5; ov.size = 1; ov.alpha = 0.9;
        ov.mask_value = { ge: 1.5 }; ov.mask_y = { lt: 4 };
      } else if (ovType === "field") {
        ov.file = `${d}/projViscosityField-${st}.h5`; ov.mesh_file = `${d}/mesh.h5`;
        ov.cmap = "viridis"; ov.alpha = 0.5; ov.log10 = true; ov.column = 0;
        ov.cbar_label = "log10 η";
      } else if (ovType === "vectors") {
        ov.file = `${d}/velocityField-${st}.h5`; ov.mesh_file = `${d}/mesh.h5`;
        ov.ux_col = 0; ov.uy_col = 1;
        ov.color = "#000000"; ov.width = 0.005; ov.alpha = 0.9;
      } else if (ovType === "tracers") {
        ov.file = `${d}/grid1-${st}.h5`; ov.files = [`${d}/grid1-${st}.h5`];
        ov.labels = ["grid1"];
        ov.colors = ["#FFD700", "#00E5FF", "#FF6B6B", "#4ADE80", "#FF9F43"];
        ov.color = "#FFD700"; ov.marker = "o"; ov.size = 5; ov.alpha = 0.95;
      }
      p.overlays.push(ov);
      renderPanels();
      savePanels();
    };
  });
  $$("#panel-list [data-act=ov-del]").forEach((btn) => {
    btn.onclick = () => {
      const p = state.panels[+btn.dataset.i];
      if (p && p.overlays) { p.overlays.splice(+btn.dataset.oi, 1); renderPanels(); savePanels(); }
    };
  });
  $$("#panel-list [data-act=ov-field]").forEach((inp) => {
    inp.addEventListener("change", (e) => {
      const p = state.panels[+e.target.dataset.i];
      if (!p || !p.overlays) return;
      const ov = p.overlays[+e.target.dataset.oi];
      if (!ov) return;
      const key = e.target.dataset.ovf;
      let v = e.target.type === "checkbox" ? e.target.checked : e.target.value;
      if (key === "levels") v = v.split(",").map(Number);
      if (["vmin", "vmax", "alpha", "size", "stride", "scale", "width", "key_uv", "cb_fraction", "cb_pad"].includes(key)) v = v === "" ? null : parseFloat(v);
      if (key === "mask_y") v = v.trim() ? { [e.target.dataset.maskop]: parseFloat(v) } : {};
      if (key === "mask_v") v = v.trim() ? { [e.target.dataset.maskop]: parseFloat(v) } : {};
      if (key === "cmap") {
        if (PRESET_CMAPS[v]) { ov.cmap_values = PRESET_CMAPS[v]; ov.cmap = v; }
        else { ov.cmap = v; delete ov.cmap_values; }
        const prev = document.getElementById(`cmap-prev-${e.target.dataset.i}-${e.target.dataset.oi}`);
        if (prev) { const cs = state.cmapColors[v] || PRESET_CMAPS[v]; if (cs && cs.length) prev.style.background = "linear-gradient(90deg," + cs.join(",") + ")"; }
        return;
      }
      if (key === "clabel_bool") { ov.clabel = v; return; }
      if (key === "cb_bool") { ov.colorbar = v; return; }
      if (key === "log10_bool") { ov.log10 = v; return; }
      if (key === "legend_bool") { ov.legend = v; return; }
      if (key === "files_str") { ov.files = v.split(",").map((s) => s.trim()).filter(Boolean); ov.file = ov.files[0] || ""; return; }
      if (key === "labels_str") { ov.labels = v.split(",").map((s) => s.trim()).filter(Boolean); return; }
      if (key === "colors_str") { ov.colors = v.split(",").map((s) => s.trim()).filter(Boolean); return; }
      ov[key] = v;
      scheduleAutoRender();
    });
  });
}

function materialCardHTML(p, i) {
  const dir = (p.step_dir || "").replace(/\/$/, "");
  const fileBase = (p.file || "").split("/").pop() || "swarm-N.h5";
  const matBase = (p.material_file || "").split("/").pop() || "materialField-N.h5";
  const dims = currentGridDims();
  const posTag = `(位置 ${Math.floor(i / Math.max(dims.cols, 1)) + 1},${(i % Math.max(dims.cols, 1)) + 1})`;
  let html = `<h4><span class="tag">物质场</span> 面板 ${i + 1} · ${posTag}
     <button class="panel-del" data-i="${i}" title="删除">✕</button></h4>`;
  if (dir) {
    html += `<label>Step（同目录面板联动） <input type="number" data-f="step" data-i="${i}" value="${p.step ?? 0}"></label>`;
  }
  html += `<label class="file-v">swarm<small> ${esc(fileBase)}</small></label>`;
  html += `<label class="file-v">material<small> ${esc(matBase)}</small></label>`;
  if (!p.material_file) {
    html += `<label>material 文件 <input data-f="material_file" data-i="${i}" value="${esc(p.material_file || "")}" placeholder="…/materialField-N.h5"></label>`;
  }
  html += `<label>材料配色 <div class="cmap-row2"><select data-f="cmap" data-i="${i}">
    <option value="Qaidam" ${(p.cmap || "Qaidam") === "Qaidam" ? "selected" : ""}>Qaidam</option>
    <option value="Earth Structure" ${p.cmap === "Earth Structure" ? "selected" : ""}>Earth Structure</option>
    <option value="Journal" ${p.cmap === "Journal" ? "selected" : ""}>Journal</option>
    <option value="tab10" ${p.cmap === "tab10" ? "selected" : ""}>tab10</option>
    </select><span class="cmap-preview" id="cmap-prev-p-${i}" style="background:linear-gradient(90deg,#FCFCFA,#F8DB83,#F7EDD9,#9D9FE3,#B8BCE3,#32583F,#DE8F21,#BEBFCB,#B2D6CC)"></span></div></label>
  <label>背景色 <input type="color" data-f="bg_color" data-i="${i}" value="${(p.bg_color && p.bg_color.startsWith("#")) ? p.bg_color : "#404040"}" class="color-input"></label>`;
  html += `<label>只画材料 id（逗号分隔，留空=全部） <input data-f="only_materials" data-i="${i}" value="${((p.only_materials || []).join(","))}" placeholder="4,7"></label>`;
  html += `<label>marker 大小 <input type="number" data-f="marker_size" data-i="${i}" value="${p.marker_size ?? 1}" step="0.5"></label>`;
  html += `<label><input type="checkbox" data-f="fast" data-i="${i}" ${p.fast ? "checked" : ""}> ⚡ 快速渲染（粒子→网格，约 10x 快，出图时建议关）</label>`;
  html += `<label>横纵比 ${aspectHTML(i, p.aspect)}</label>`;
  html += `<label>图例位置
    <select data-f="legend_loc" data-i="${i}">
      ${["best","lower center","upper left","upper right","lower left","lower right","outside right","outside bottom"].map(l => `<option value="${l}" ${(p.legend_loc || "best") === l ? "selected" : ""}>${l}</option>`).join("")}
    </select></label>`;
  html += `<label><input type="checkbox" data-f="legend" data-i="${i}" ${p.legend === false ? "" : "checked"}> 材料图例</label>`;
  // 叠加层
  html += `<div class="ovs">`;
  (p.overlays || []).forEach((ov, oi) => {
    const ovName = (ov.file || "").split("/").pop() || ov.ov_type || ov.type;
    const cnt = { contour: "温度等值线", scatter: "应变散点", field: "场叠加",
                  vectors: "速度矢量", tracers: "追踪点" }[ov.type] || ov.type;
    html += `<div class="ov-row">
      <span class="ov-tag">${cnt}</span> <small>${esc(ovName)}</small>
      <button class="ov-del" data-act="ov-del" data-i="${i}" data-oi="${oi}" title="删除">✕</button>
      <details open><summary>参数</summary>`;
    if (ov.type === "contour") {
      html += `<label>levels (K,逗号) <input data-act="ov-field" data-ovf="levels" data-i="${i}" data-oi="${oi}" value="${(ov.levels || []).join(",")}"></label>`;
      html += `<label>颜色 <input type="color" data-act="ov-field" data-ovf="color" data-i="${i}" data-oi="${oi}" value="${(ov.color && ov.color.startsWith("#")) ? ov.color : "#ff557f"}" class="color-input"></label>`;
      html += `<label><input type="checkbox" data-act="ov-field" data-ovf="clabel_bool" data-i="${i}" data-oi="${oi}" ${ov.clabel === false ? "" : "checked"}> 标注温度</label>`;
    } else if (ov.type === "scatter") {
      html += `<label>colormap ${cmapSelectHTML(i, oi, ov.cmap, "hot_r")}</label>`;
      html += `<label>vmin <input type="number" data-act="ov-field" data-ovf="vmin" data-i="${i}" data-oi="${oi}" value="${ov.vmin ?? ""}"></label>`;
      html += `<label>vmax <input type="number" data-act="ov-field" data-ovf="vmax" data-i="${i}" data-oi="${oi}" value="${ov.vmax ?? ""}"></label>`;
      html += `<label>值阈值 (≥) <input data-act="ov-field" data-ovf="mask_v" data-maskop="ge" data-i="${i}" data-oi="${oi}" value="${(ov.mask_value && ov.mask_value.ge) ?? ""}"></label>`;
      html += `<label>y 上限 (<) <input data-act="ov-field" data-ovf="mask_y" data-maskop="lt" data-i="${i}" data-oi="${oi}" value="${(ov.mask_y && ov.mask_y.lt) ?? ""}"></label>`;
      html += `<label><input type="checkbox" data-act="ov-field" data-ovf="cb_bool" data-i="${i}" data-oi="${oi}" ${ov.colorbar ? "checked" : ""}> colorbar</label>`;
    } else if (ov.type === "field") {
      html += `<label>colormap ${cmapSelectHTML(i, oi, ov.cmap, "viridis")}</label>`;
      html += `<label>alpha <input type="number" step="0.1" data-act="ov-field" data-ovf="alpha" data-i="${i}" data-oi="${oi}" value="${ov.alpha ?? 0.5}"></label>`;
      html += `<label><input type="checkbox" data-act="ov-field" data-ovf="log10_bool" data-i="${i}" data-oi="${oi}" ${ov.log10 ? "checked" : ""}> log10</label>`;
    } else if (ov.type === "vectors") {
      html += `<label>文件 <input data-act="ov-field" data-ovf="file" data-i="${i}" data-oi="${oi}" value="${esc(ov.file || "")}" placeholder="…/velocityField-N.h5"></label>`;
      html += `<label>颜色 (hex 或 speed)
        <input type="color" data-act="ov-field" data-ovf="color" data-i="${i}" data-oi="${oi}" value="${(ov.color && ov.color.startsWith("#")) ? ov.color : "#000000"}" class="color-input">
        <input type="text" data-act="ov-field" data-ovf="color" data-i="${i}" data-oi="${oi}" value="${esc(ov.color || "#000000")}" placeholder="#000000 或 speed" style="margin-top:3px">
      </label>`;
      html += `<label>stride (隔 n 点画一箭头)<input type="number" data-act="ov-field" data-ovf="stride" data-i="${i}" data-oi="${oi}" value="${ov.stride ?? ""}" placeholder="自动"></label>`;
      html += `<label>scale<input type="number" step="any" data-act="ov-field" data-ovf="scale" data-i="${i}" data-oi="${oi}" value="${ov.scale ?? ""}" placeholder="自动"></label>`;
      html += `<label>width<input type="number" step="0.001" data-act="ov-field" data-ovf="width" data-i="${i}" data-oi="${oi}" value="${ov.width ?? 0.005}"></label>`;
      html += `<label>key_uv (参考箭头)<input type="number" step="any" data-act="ov-field" data-ovf="key_uv" data-i="${i}" data-oi="${oi}" value="${ov.key_uv ?? ""}" placeholder="如 2"></label>`;
      html += `<label>key_text <input data-act="ov-field" data-ovf="key_text" data-i="${i}" data-oi="${oi}" value="${esc(ov.key_text || "")}" placeholder="如 2 cm/yr"></label>`;
    } else if (ov.type === "tracers") {
      html += `<label>文件 (逗号分隔多个)<input data-act="ov-field" data-ovf="files_str" data-i="${i}" data-oi="${oi}" value="${esc((ov.files || [ov.file] || []).join(","))}" placeholder="…/grid1-N.h5,…/grid2-N.h5"></label>`;
      html += `<label>标签 (逗号分隔)<input data-act="ov-field" data-ovf="labels_str" data-i="${i}" data-oi="${oi}" value="${esc((ov.labels || []).join(","))}" placeholder="grid1,grid2"></label>`;
      html += `<label>颜色 (逗号分隔)<input data-act="ov-field" data-ovf="colors_str" data-i="${i}" data-oi="${oi}" value="${esc((ov.colors || [ov.color || "#FFD700"]).join(","))}"></label>`;
      html += `<label>marker<input data-act="ov-field" data-ovf="marker" data-i="${i}" data-oi="${oi}" value="${esc(ov.marker || "o")}"></label>`;
      html += `<label>size<input type="number" step="0.5" data-act="ov-field" data-ovf="size" data-i="${i}" data-oi="${oi}" value="${ov.size ?? 1}"></label>`;
      html += `<label>alpha<input type="number" step="0.05" data-act="ov-field" data-ovf="alpha" data-i="${i}" data-oi="${oi}" value="${ov.alpha ?? 0.9}"></label>`;
      html += `<label><input type="checkbox" data-act="ov-field" data-ovf="legend_bool" data-i="${i}" data-oi="${oi}" ${ov.legend ? "checked" : ""}> 图例</label>`;
    }
    html += `</details></div>`;
  });
  html += `</div>`;
  html += `<div class="btn-row">
    <button class="mini" data-act="ov-add" data-ov="contour" data-i="${i}">+温度等值线</button>
    <button class="mini" data-act="ov-add" data-ov="scatter" data-i="${i}">+应变散点</button>
    <button class="mini" data-act="ov-add" data-ov="vectors" data-i="${i}">+速度矢量</button>
    <button class="mini" data-act="ov-add" data-ov="tracers" data-i="${i}">+追踪点</button>
    <button class="mini" data-act="ov-add" data-ov="field" data-i="${i}">+场叠加</button>
  </div>`;
  html += `<details><summary>坐标/标签/高级</summary>
    <label>x lim <input data-f="xlim" data-i="${i}" value="${(p.xlim || []).join(",")}" placeholder="0,800"></label>
    <label>y lim <input data-f="ylim" data-i="${i}" value="${(p.ylim || []).join(",")}" placeholder="-150,10"></label>
    <label>x label <input data-f="xlabel" data-i="${i}" value="${esc(p.xlabel || "x [km]")}"></label>
    <label>y label <input data-f="ylabel" data-i="${i}" value="${esc(p.ylabel || "y [km]")}"></label>
    ${advancedHTML(i, p, { marker: true })}
  </details>`;
  return html;
}

function applyStep(p, step) {
  const d = (p.step_dir || "").replace(/\/$/, "");
  if (!d) return p;
  const repl = (f) => {
    if (!f) return f;
    const m = f.match(/^(.*\/)([^/]+?)(\d+)\.(h5|hdf5|hdf)$/i);
    if (m && m[1].replace(/\/$/, "") === d) return `${d}/${m[2]}${step}.${m[4]}`;
    return f;
  };
  p.step = step;
  p.file = repl(p.file);
  p.material_file = repl(p.material_file);
  if (p.overlays) p.overlays.forEach((o) => { o.file = repl(o.file); });
  return p;
}

/* ---- 内置预设色板（与 core/config.py 一致） ---- */
const PRESET_CMAPS = {
  "Qaidam": ["#FCFCFA", "#F8DB83", "#F7EDD9", "#9D9FE3", "#B8BCE3", "#32583F", "#DE8F21", "#BEBFCB", "#B2D6CC"],
  "Earth Structure": ["#D9D9FF", "#EE650A", "#FCD97A", "#37889F", "#3260A4", "#83CC92"],
  "Journal": ["#2878B5", "#D97924", "#2CA02C", "#D7191C", "#444444"],
};

function fillCmapSelect(sel) {
  const presets = Object.keys(PRESET_CMAPS);
  const conts = ["turbo", "viridis", "plasma", "inferno", "magma", "cividis",
    "coolwarm", "RdBu_r", "hot_r", "hot", "Blues", "Oranges", "Greens", "Reds", "bone", "gray",
    "tab10", "Set1", "Dark2"];
  const opts = [
    `<optgroup label="内置预设">` + presets.map((o) => `<option value="${o}">${o}</option>`).join("") + `</optgroup>`,
    `<optgroup label="连续色板">` + conts.map((o) => `<option value="${o}">${o}</option>`).join("") + `</optgroup>`,
  ].join("");
  sel.innerHTML = opts;
}

/* 色板预览条（渐变） */
function cmapPreviewHTML(name, idSuffix) {
  const colors = state.cmapColors[name] || PRESET_CMAPS[name] || null;
  if (!colors || !colors.length) return "";
  const bg = "linear-gradient(90deg," + colors.map((c) => c).join(",") + ")";
  return `<span class="cmap-preview" id="${idSuffix}" style="background:${bg}"></span>`;
}

/* 单色选择（弹出系统颜色板） */
function colorFieldHTML(label, attrs, value, opts = {}) {
  const v = (value && value.startsWith("#") && value.length === 7) ? value : (opts.fallback || "#ff557f");
  const extra = opts.allowNone ? `<input type="text" data-${attrs} value="${esc(value || "")}" placeholder="none" style="margin-top:3px">` : "";
  return `<label>${label}
    <input type="color" data-${attrs} value="${v}" class="color-input">
    ${extra}</label>`;
}

/* 叠加层/面板的 colormap 下拉 HTML（含内置预设 + 连续色板） */
function cmapSelectHTML(i, oi, current, fallback) {
  const presets = Object.keys(PRESET_CMAPS);
  const conts = ["turbo", "viridis", "plasma", "inferno", "magma", "cividis",
    "coolwarm", "RdBu_r", "hot_r", "hot", "Blues", "Oranges", "Greens", "Reds", "bone", "gray",
    "tab10", "Set1", "Dark2"];
  const val = current || fallback || "turbo";
  const opt = (v, lbl) => `<option value="${v}" ${val === v ? "selected" : ""}>${lbl || v}</option>`;
  return `<div class="cmap-row2">` +
    `<select data-act="ov-field" data-ovf="cmap" data-i="${i}" data-oi="${oi}">` +
    `<optgroup label="内置预设">` + presets.map((o) => opt(o)).join("") + `</optgroup>` +
    `<optgroup label="连续色板">` + conts.map((o) => opt(o)).join("") + `</optgroup>` +
    `</select>` +
    cmapPreviewHTML(val, `cmap-prev-${i}-${oi}`) +
    `</div>`;
}

/* 高级参数 HTML（网格/log/边框/marker/colorbar 等，全部 UI 可调） */
function advancedHTML(i, p, opts = {}) {
  const chk = (f, label, cur) => `<label class="chk"><input type="checkbox" data-f="${f}" data-i="${i}" ${cur ? "checked" : ""}> ${label}</label>`;
  const sel = (f, options, cur) => `<select data-f="${f}" data-i="${i}">` +
    options.map(([v, lbl]) => `<option value="${v}" ${String(cur) === String(v) ? "selected" : ""}>${lbl}</option>`).join("") + `</select>`;
  let h = "";
  h += chk("grid", "网格线", p.grid);
  h += `<label>网格样式 ${sel("grid_ls", [["--", "虚线"], [":", "点线"], ["-", "实线"]], p.grid_ls || "--")}</label>`;
  h += `<label>网格颜色 <input type="color" data-f="grid_color" data-i="${i}" value="${(p.grid_color && p.grid_color.startsWith("#")) ? p.grid_color : "#CCCCCC"}" class="color-input"></label>`;
  h += chk("xscale_log", "x 轴 log", p.xscale_log);
  h += chk("yscale_log", "y 轴 log", p.yscale_log);
  h += chk("spines_all", "显示上/右边框", p.spines_all);
  if (opts.vmin) {
    h += `<label>vmin <input type="number" step="any" data-f="vmin" data-i="${i}" value="${p.vmin ?? ""}"></label>`;
    h += `<label>vmax <input type="number" step="any" data-f="vmax" data-i="${i}" value="${p.vmax ?? ""}"></label>`;
  }
  if (opts.marker) {
    h += `<label>marker 形状 ${sel("marker", [["o", "o 圆点"], ["s", "s 方块"], ["^", "^ 三角"], ["D", "D 菱形"], ["x", "x 叉"], ["+", "+ 加号"], ["*", "* 星"], ["."], ["."]], p.marker || "o")}</label>`;
    h += `<label>边缘色（none=无）<input data-f="edgecolors" data-i="${i}" value="${esc(p.edgecolors || "none")}"></label>`;
  }
  if (opts.cb) {
    h += `<label>colorbar 位置 ${sel("cb_location", [["", "right"], ["bottom", "bottom"], ["top", "top"], ["left", "left"]], p.cb_location || "")}</label>`;
    h += `<label>cb fraction <input type="number" step="0.005" data-f="cb_fraction" data-i="${i}" value="${p.cb_fraction ?? 0.046}"></label>`;
    h += `<label>cb pad <input type="number" step="0.005" data-f="cb_pad" data-i="${i}" value="${p.cb_pad ?? 0.04}"></label>`;
  }
  return h;
}

/* 横纵比 HTML（自动/数据等比/自定义数字） */
function aspectHTML(i, current) {
  const num = (typeof current === "number" || (typeof current === "string" && current !== "" && !["equal", "data", "1", "auto", "custom"].includes(current)))
    ? current : "";
  const selVal = current === "equal" ? "equal" : (num !== "" ? "custom" : "");
  return `<select data-f="aspect" data-i="${i}">
      <option value="" ${selVal === "" ? "selected" : ""}>自动</option>
      <option value="equal" ${selVal === "equal" ? "selected" : ""}>数据等比 (x:y 同尺度)</option>
      <option value="custom" ${selVal === "custom" ? "selected" : ""}>自定义…</option>
    </select>
    <label id="aspect-num-row-${i}" class="hidden" style="margin-top:4px">自定义数值 (y 相对 x 拉伸倍数)
      <input type="number" step="0.1" min="0.1" data-f="aspect_num" data-i="${i}" value="${esc(num)}" placeholder="如 3.5">
    </label>`;
}

/* ---------------- 渲染 / 导出 ---------------- */
function collectSpec() {
  const style = {
    font_family: $("#cfg-font").value,
    font_size: parseFloat($("#cfg-font-size").value) || 7,
    axes_label_size: parseFloat($("#cfg-label-size").value) || 8,
    legend_size: parseFloat($("#cfg-legend-size").value) || 6.5,
    line_width: parseFloat($("#cfg-linewidth").value) || 0.75,
    tick_direction: $("#cfg-tick-dir").value,
    svg_fonttype: $("#cfg-svgtext").checked ? "none" : "keep",
    panel_label_size: 10,
  };
  const panels = state.panels.map((p) => {
    // 时间自动对齐：material 面板按 step 重写所有同目录文件后缀
    if (p.kind === "material" && p.step_dir && p.step != null) {
      applyStep(p, p.step);
    }
    const out = { ...p, file: p.file || (state.fileInfo && state.fileInfo.path) };
    delete out.columns_str;
    if (p.kind === "curve") {
      out.columns = p.columns || (p.columns_str ? p.columns_str.split(",").map(Number) : [0]);
    }
    if (p.kind === "field" && !p.mesh_file && state.fileInfo) {
      out.mesh_file = p.mesh_file || (state.fileInfo.path.replace(/[^/]+$/, "") + "mesh.h5");
    }
    return out;
  });
  return {
    orientation: $("#cfg-orientation").value,
    style,
    layout: collectLayout(),
    auto_panel_labels: $("#cfg-panel-labels").checked,
    engine: ($("#cfg-engine") || {}).value || "matplotlib",
    panels,
  };
}

function collectLayout() {
  const layout = {};
  const rows = parseInt($("#cfg-rows").value, 10);
  const cols = parseInt($("#cfg-cols").value, 10);
  const hrEl = $("#cfg-height-ratios");
  const wrEl = $("#cfg-width-ratios");
  const hr = hrEl ? hrEl.value.trim() : "";
  const wr = wrEl ? wrEl.value.trim() : "";
  if (!isNaN(rows) && rows > 0) layout.rows = rows;
  if (!isNaN(cols) && cols > 0) layout.cols = cols;
  if (hr) layout.height_ratios = hr;
  if (wr) layout.width_ratios = wr;
  return Object.keys(layout).length ? layout : undefined;
}

function currentGridDims() {
  const layout = collectLayout() || {};
  const n = state.panels.length;
  let rows, cols;
  if (layout.rows && layout.cols) { rows = layout.rows; cols = layout.cols; }
  else if (layout.rows) { rows = layout.rows; cols = Math.ceil(n / rows); }
  else if (layout.cols) { cols = layout.cols; rows = Math.ceil(n / cols); }
  else if (n <= 0) { rows = cols = 1; }
  else if (n === 1) { rows = cols = 1; }
  else if (n === 2) { rows = 2; cols = 1; }
  else if (n <= 4) { rows = cols = 2; }
  else { rows = Math.ceil(n / 2); cols = 2; }
  return { rows, cols };
}

let autoRenderTimer = null;
function scheduleAutoRender() {
  // 参考 ParaView 交互式渲染：参数调整后自动重绘（已有渲染结果时才触发）
  if (!state.plotMeta) return;
  clearTimeout(autoRenderTimer);
  autoRenderTimer = setTimeout(() => renderPlot(), 650);
}

async function renderPlot() {
  const status = $("#plot-status");
  status.textContent = "渲染中…";
  status.classList.remove("err");
  try {
    const spec = collectSpec();
    if (!spec.panels.length) { status.textContent = "请先添加至少一个面板（或在检视器里点「发送到绘图」）"; status.classList.add("err"); return; }
    state.plotMeta = await api("/api/plot", spec);
    const img = $("#plot-img");
    img.src = state.plotMeta.files.png + "?t=" + Date.now();
    $("#plot-wrap").classList.remove("hidden");
    img.onload = () => {
      status.textContent = `✓ 已渲染 ${state.plotMeta.panels.length} 个面板 · A4 ${state.plotMeta.orientation} · 点击图中任意位置读数`;
      buildProbeMarkers();
    };
    saveConfigSilent();
  } catch (e) {
    status.textContent = "✕ " + String(e.message || e);
    status.classList.add("err");
  }
}

async function exportPlot() {
  if (!state.plotMeta) { toast("请先渲染一次", true); return; }
  let destDir = $("#cfg-export-dir").value.trim();
  if (!destDir) {
    const first = state.plotMeta.panels[0];
    destDir = first && first.file ? first.file.replace(/[^/]+$/, "") : "";
  }
  try {
    const r = await api("/api/export", {
      plot_id: state.plotMeta.plot_id, dest_dir: destDir,
    });
    const names = Object.entries(r.wrote).map(([k, v]) => `${k}:${v.split("/").pop()}`).join(" · ");
    toast(`已导出 → ${destDir}  ${names}`);
  } catch (e) { toast("导出失败: " + String(e.message || e), true); }
}

/* ---------------- 点击 probe ---------------- */
function onPlotClick(e) {
  const img = $("#plot-img");
  if (!state.plotMeta) return;
  const rect = img.getBoundingClientRect();
  const nw = img.naturalWidth || rect.width, nh = img.naturalHeight || rect.height;
  const px = (e.clientX - rect.left) * (nw / rect.width);
  const py = (e.clientY - rect.top) * (nh / rect.height);
  api("/api/probe", {
    plot_id: state.plotMeta.plot_id, px_x: px, px_y: py,
    fig_w_px: nw, fig_h_px: nh,
  }).then((r) => {
    const tip = $("#probe-tip");
    if (!r.hit) { tip.style.display = "none"; return; }
    let txt = `panel ${r.panel + 1} (${r.kind}) · x=${r.x}  y=${r.y}`;
    const reads = Object.entries(r.values || {})
      .filter(([k]) => k !== "nearest_index")
      .map(([k, v]) => `${k}=${v}`).join(" · ");
    if (reads) txt += "<br>" + reads;
    tip.innerHTML = txt;
    tip.style.display = "block";
    positionTip(e);
    $("#probe-readout").textContent = `📍 ${txt.replace(/<br>/g, "  |  ")}   (可截图/参考，不影响导出图)`;
  }).catch((err) => toast("探针失败: " + err.message, true));
}

function positionTip(e) {
  const box = $("#plot-image-box");
  const tip = $("#probe-tip");
  const rect = box.getBoundingClientRect();
  let x = e.clientX - rect.left + 14, y = e.clientY - rect.top + 14;
  if (x + 220 > rect.width) x -= tip.offsetWidth + 24;
  if (y + 90 > rect.height) y -= 70;
  tip.style.left = x + "px";
  tip.style.top = y + "px";
}

function moveTip(e) {
  if ($("#probe-tip").style.display === "block") positionTip(e);
}

function buildProbeMarkers() {
  // 预留：绘制面板外框等。当前探针直接点击即可。
}

/* ---------------- 配置 ---------------- */
function applyConfigToUI(cfg) {
  const st = cfg.style || {};
  const lay = cfg.layout || {};
  if (lay.rows) $("#cfg-rows").value = lay.rows;
  if (lay.cols) $("#cfg-cols").value = lay.cols;
  const hrEl = $("#cfg-height-ratios");
  const wrEl = $("#cfg-width-ratios");
  if (hrEl && lay.height_ratios) hrEl.value = Array.isArray(lay.height_ratios) ? lay.height_ratios.join(",") : lay.height_ratios;
  if (wrEl && lay.width_ratios) wrEl.value = Array.isArray(lay.width_ratios) ? lay.width_ratios.join(",") : lay.width_ratios;
  $("#cfg-font").value = st.font_family || "Arial";
  $("#cfg-font-size").value = st.font_size ?? 7;
  $("#cfg-label-size").value = st.axes_label_size ?? 8;
  $("#cfg-legend-size").value = st.legend_size ?? 6.5;
  $("#cfg-linewidth").value = st.line_width ?? 0.75;
  $("#cfg-tick-dir").value = st.tick_direction || "in";
  $("#cfg-orientation").value = cfg.orientation || "portrait";
  const eng = document.getElementById("cfg-engine");
  if (eng && cfg.engine) eng.value = cfg.engine;
  if (st.svg_fonttype === "none") $("#cfg-svgtext").checked = true;
  if (cfg.auto_panel_labels === false) $("#cfg-panel-labels").checked = false;
}

function saveConfigSilent() {
  const spec = collectSpec();
  api("/api/config", { config: {
    orientation: spec.orientation,
    style: spec.style,
    layout: spec.layout,
    auto_panel_labels: spec.auto_panel_labels,
    engine: spec.engine,
  } }).catch(() => {});
}

/* ---------------- 启动 ---------------- */
document.addEventListener("DOMContentLoaded", boot);