#!/bin/bash

# CARE Bot Installation Script

echo "Installing CARE Bot dependencies..."

pip install --upgrade pip

# Use latest versions (not pinned old versions)
pip install google-genai # Need latest for gemini-1.5-flash
pip install chromadb
pip install sentence-transformers
pip install python-dotenv
pip install pypdf

echo "✅ Installation complete!"
python main.py