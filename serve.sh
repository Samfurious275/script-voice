#!/bin/bash
# Opens the script-to-voiceover page in your browser.
# First run creates the environment; after that it starts in seconds.
set -e
cd "$(dirname "$0")"

find_python() {
  for c in python3 python3.13 python3.12 python3.11 python; do
    command -v "$c" >/dev/null 2>&1 || continue
    "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null \
      && { echo "$c"; return 0; }
  done
  return 1
}

if [ ! -x .venv/bin/python ]; then
  PY="$(find_python)" || {
    echo "Python 3.9 or newer is required but was not found."
    echo "  macOS:          brew install python"
    echo "  Debian/Ubuntu:  sudo apt install python3 python3-venv"
    exit 1
  }
  echo "Setting up (one minute, once)..."
  "$PY" -m venv .venv
  .venv/bin/pip install --upgrade pip >/dev/null
  .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/python serve.py "$@"
