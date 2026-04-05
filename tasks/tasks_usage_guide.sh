#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

describe_script() {
  case "$1" in
    start_fastapi.sh)
      echo "FastAPI (uvicorn) をバックグラウンド起動します。"
      ;;
    start_fastapi_log.sh)
      echo "FastAPI (uvicorn) をフォアグラウンド起動し、ログを表示します。"
      ;;
    stop_fastapi.sh)
      echo "実行中の uvicorn プロセスを停止します。"
      ;;
    check_fastapi_status.sh)
      echo "http://127.0.0.1:8000 に curl して応答を確認します。"
      ;;
    tasks_usage_guide.sh)
      echo "この一覧 (使い方と説明) を表示します。"
      ;;
    *)
      echo "説明未登録のスクリプトです。"
      ;;
  esac
}

echo "tasks 配下のシェルスクリプト一覧"
echo

for script_path in "$SCRIPT_DIR"/*.sh; do
  script_name="$(basename "$script_path")"
  echo "- $script_name"
  echo "  実行方法: ./tasks/$script_name"
  echo "  実行方法: bash ./tasks/$script_name"
  echo "  説明: $(describe_script "$script_name")"
  echo
done
