#!/usr/bin/env bash
set -euo pipefail

pkill -f uvicorn || true
echo "Stopped uvicorn processes (if any were running)."
