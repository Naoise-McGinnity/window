#!/bin/bash

# Check for python3
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is not installed. Please install it from https://www.python.org/downloads/"
    exit 1
fi

# Create virtual environment if missing
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment and installing requirements..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pyobjc

echo "Running the game..."
python 2d.py

deactivate