#!/usr/bin/env bash
# 웹(WebAssembly) 버전 빌드: 필요한 소스만 스테이징한 뒤 pygbag으로 변환.
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-.venv/bin/python}"

"$PYTHON" -m pip install -q -r requirements-web.txt
rm -rf build/web-src
mkdir -p build/web-src
cp main.py build/web-src/
cp -r lunar_lander build/web-src/
cp assets/icon.png build/web-src/favicon.png
find build/web-src -name "__pycache__" -type d -exec rm -rf {} +
"$PYTHON" -m pygbag --build --title "Moon Descent" --icon build/web-src/favicon.png build/web-src
echo "웹 빌드 완료: build/web-src/build/web/"
