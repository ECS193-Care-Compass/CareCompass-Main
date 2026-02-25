#!/bin/bash

# CARE Bot Installation Script

echo "Installing CARE Bot dependencies..."

pip install --upgrade pip

pip install google-genai
pip install chromadb
pip install sentence-transformers
pip install python-dotenv
pip install pypdf
pip install fastapi
pip install uvicorn
pip install transformers
pip install torch

echo "Installation complete!"
