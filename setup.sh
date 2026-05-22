#!/bin/bash

echo "Setting up Launchpad virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing requirements..."
pip install -r requirements.txt
playwright install chromium

echo "Setup complete!"
echo "Please ensure you have added your API keys to .env and configured config.yaml."
