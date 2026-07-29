#!/usr/bin/env bash
# 원커맨드 배포: 커밋/푸시 → 클라우드 빌드 → release/ 폴더에 결과 다운로드.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"

gh auth status >/dev/null 2>&1 || { echo "먼저 GitHub 로그인이 필요합니다: gh auth login"; exit 1; }

git add -A
git diff --cached --quiet || git commit -m "release: $(date +%F)"
git push origin main

prev=$(gh run list --workflow=build.yml --limit 1 --json databaseId --jq '.[0].databaseId // 0' 2>/dev/null || echo 0)
gh workflow run build.yml --ref main
echo "클라우드 빌드가 시작되기를 기다리는 중..."
run_id=$prev
for _ in $(seq 1 24); do
  sleep 5
  run_id=$(gh run list --workflow=build.yml --limit 1 --json databaseId --jq '.[0].databaseId // 0' 2>/dev/null || echo 0)
  if [ "$run_id" != "$prev" ] && [ "$run_id" != "0" ]; then break; fi
done
if [ "$run_id" = "$prev" ] || [ "$run_id" = "0" ]; then echo "빌드 실행을 찾지 못했습니다. github.com 저장소의 Actions 탭을 확인하세요."; exit 1; fi

gh run watch "$run_id" --exit-status
rm -rf release && mkdir release
gh run download "$run_id" --dir release -p "MoonDescent-*"
echo
echo "=== 배포 파일 완성 (release/) ==="
find release -type f | sed 's/^/  /'
echo
echo "전달: Windows → MoonDescent-windows.zip, 맥 → MoonDescent-macos.zip, 리눅스 → MoonDescent-linux.tar.gz"
echo "카카오톡이나 Dropbox 공유 링크로 보내세요. (Gmail 첨부는 exe가 든 zip을 차단합니다)"
echo "웹 버전도 자동 배포되었습니다. 링크만 공유해도 됩니다: https://pjw-project-portfolio.github.io/moon-descent/"
