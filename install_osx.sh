#!/bin/bash

VENV="$HOME/.local/share/venvs/inkscape"

INK_PY=$(\
      find /Applications/Inkscape.app \
      -type f \
      -path "*/Python.framework/Versions/*/bin/python3*" \
      -not -path "*/Python.framework/Versions/*/bin/python3*-*" \
      | sort -V | tail -n1 \
  )

if [ -x "$INK_PY" ]; then
    echo "Using Inkscape Python: $INK_PY"
else
    echo "Could not find Inkscape Python. Got: '$INK_PY'"
    echo "Bailing out."
    exit -1
fi

echo "Removing old venv (if any)..."
rm -rf "$VENV"
mkdir -p "$(dirname "$VENV")"

echo "Creating new venv (inherits Inkscape's packages)..."
"$INK_PY" -m venv --system-site-packages "$VENV"

echo "Activating and chaining up to second stage install"
source "$VENV/bin/activate"
python -m ensurepip -U || true
pip install --upgrade pip

./install_osx_stage2.py
