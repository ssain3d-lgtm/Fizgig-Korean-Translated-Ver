#!/bin/sh
# Fizgig 한글화 설치 (Linux / macOS).  Windows 는 한글화_설치.bat 을 쓰세요.
#
#   ./install_ko.sh                       이 폴더가 Fizgig 폴더 안에 있을 때
#   ./install_ko.sh /path/to/Fizgig       그 외의 경우 Fizgig 폴더를 직접 지정
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
REPO=${1:-$(dirname "$DIR")}
PY="$REPO/venv/bin/python"
if [ ! -x "$PY" ]; then
    echo "Fizgig 의 venv 를 찾지 못했습니다: $PY" >&2
    echo "Fizgig 폴더 경로를 인자로 넘겨 주세요:  ./install_ko.sh /path/to/Fizgig" >&2
    exit 1
fi
exec "$PY" "$DIR/tools/install.py"
