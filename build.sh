#!/usr/bin/env bash
# Build the Linux one-file executable and install the GNOME launcher.
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt -r requirements-build.txt

.venv/bin/python -m PyInstaller --noconfirm --onefile --name LunarLander \
  --add-data "lunar_lander/assets/fonts:lunar_lander/assets/fonts" main.py

# Frozen smoke test: binary must survive 8s under dummy video/audio drivers.
(
  export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  ./dist/LunarLander &
  pid=$!
  sleep 8
  kill -0 "$pid" 2>/dev/null || { echo "SMOKE FAIL: binary exited early"; exit 1; }
  kill "$pid"
)
echo "SMOKE OK"

# GNOME app-grid launcher (Exec quoted because the path contains a space).
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/lunar-lander.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Lunar Lander
Comment=Vector-style lunar landing game
Exec="$PWD/dist/LunarLander"
Icon=$PWD/assets/icon.png
Terminal=false
Categories=Game;
EOF
echo "완료: 앱 그리드에서 'Lunar Lander'를 실행할 수 있습니다."
