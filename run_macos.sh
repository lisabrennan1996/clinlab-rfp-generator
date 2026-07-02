#!/bin/bash
echo "============================================"
echo " Central Lab RFP Generator"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 not found."
    echo "Install: brew install python@3.12"
    exit 1
fi

# Create venv if missing
if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv venv
fi

# Install deps
echo "[2/3] Installing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# Launch
echo "[3/3] Launching RFP Generator..."
echo ""
python3 run.py
