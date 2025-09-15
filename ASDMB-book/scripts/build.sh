#!/usr/bin/env bash
set -Eeuo pipefail

# Resolve this script's directory even if called via symlink
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Prefer python3 if available
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

# Run the generator
"$PY" "$SCRIPT_DIR/build_schedule.py"
