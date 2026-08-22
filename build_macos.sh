#!/bin/bash
# ============================================================
# H5TOUWG — macOS 打包脚本（Apple Silicon / arm64）
# 产物：dist/H5TOUWG.app + dist/H5TOUWG-<ver>-<arch>.dmg
#
# 用法：
#   conda activate geopixel
#   bash build_macos.sh
#
# 说明：
# - 产物仅适配构建机的架构（本脚本默认 arm64；Intel Mac 需在
#   Intel 机器上运行本脚本，或安装对应架构 Python 后重新构建）
# - 目标 Mac 无需安装 Python / 依赖，双击 .app 即用
# - 数据只读模型目录；userdata 写入 ~/Library/Application Support/H5PlotStudio/
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="PlotUWG"
VERSION="0.6.2"
ARCH="$(python -c 'import platform; print(platform.machine())')"

echo "==> 清理旧构建"
rm -rf build dist *.spec

echo "==> PyInstaller 打包(${ARCH})"
pyinstaller --noconfirm --clean \
  --name "${APP_NAME}" \
  --windowed \
  --osx-bundle-identifier "com.h5touwg" \
  --icon "H5TOUWG.icns" \
  --add-data "web:web" \
  --add-data "rust_bin/h5render:rust_bin" \
  --add-data "core/data:core/data" \
  --hidden-import app \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets.auto \
  --collect-data matplotlib \
  --collect-submodules matplotlib \
  --collect-submodules h5py \
  run_app.py

echo "==> 产物: dist/${APP_NAME}.app"
echo "==> 打 DMG"
dmg_name="dist/${APP_NAME}-${VERSION}-${ARCH}.dmg"
rm -f "${dmg_name}"
hdiutil create -volname "PlotUWG" -srcfolder "dist/${APP_NAME}.app" \
  -ov -format UDZO "${dmg_name}" >/dev/null

echo ""
echo "✅ 完成："
echo "   App : dist/${APP_NAME}.app"
echo "   DMG : ${dmg_name}"
echo "   （拷贝 DMG 到其他 MacBook 双击安装即可；仅支持 ${ARCH} 架构）"
