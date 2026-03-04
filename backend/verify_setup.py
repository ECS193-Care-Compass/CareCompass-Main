#!/usr/bin/env python3
"""
Setup verification script for CARE Bot
Checks that all requirements are met before running
"""
import sys
import os
from pathlib import Path

# Resolve project root (one level above backend/)
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python version too old: {version.major}.{version.minor}.{version.micro}")
        print("  Required: Python 3.8+")
        return False

def check_env_file():
    """Check if .env file exists and has API key"""
    env_path = PROJECT_ROOT / ".env"
    
    if not env_path.exists():
        print("✗ .env file not found")
        print("  Run: cp .env.example .env")
        print("  Then add your GOOGLE_API_KEY")
        return False
    
    with open(env_path) as f:
        content = f.read()
        if "your_api_key_here" in content or "GOOGLE_API_KEY=" not in content:
            print("✗ .env file exists but API key not configured")
            print("  Edit .env and add your Google API key")
            return False
    
    print("✓ .env file configured")
    return True

def check_dependencies():
    """Check if key dependencies are installed"""
    missing = []
    
    try:
        import google.generativeai
        print("✓ google-generativeai installed")
    except ImportError:
        missing.append("google-generativeai")
    
    try:
        import chromadb
        print("✓ chromadb installed")
    except ImportError:
        missing.append("chromadb")
    
    try:
        import sentence_transformers
        print("✓ sentence-transformers installed")
    except ImportError:
        missing.append("sentence-transformers")
    
    try:
        import pypdf
        print("✓ pypdf installed")
    except ImportError:
        missing.append("pypdf")
    
    if missing:
        print(f"✗ Missing dependencies: {', '.join(missing)}")
        print("  Run: pip install -r requirements.txt")
        return False
    
    return True

def check_data_directory():
    """Check if data directories exist"""
    raw_dir = PROJECT_ROOT / "data" / "raw"
    
    if not raw_dir.exists():
        print("✗ data/raw directory not found")
        return False
    
    pdfs = list(raw_dir.glob("*.pdf"))
    if not pdfs:
        print("✗ No PDF files found in data/raw/")
        print("  Add your documents to data/raw/")
        return False
    
    print(f"✓ Found {len(pdfs)} PDF(s) in data/raw/")
    for pdf in pdfs:
        print(f"  - {pdf.name}")
    
    return True

def check_structure():
    """Check project structure"""
    required_dirs = {
        "backend/config": BACKEND_DIR / "config",
        "backend/src/embeddings": BACKEND_DIR / "src" / "embeddings",
        "backend/src/retrieval": BACKEND_DIR / "src" / "retrieval",
        "backend/src/generation": BACKEND_DIR / "src" / "generation",
        "backend/src/safety": BACKEND_DIR / "src" / "safety",
        "backend/src/utils": BACKEND_DIR / "src" / "utils",
        "data/raw": PROJECT_ROOT / "data" / "raw",
        "backend/tests": BACKEND_DIR / "tests",
    }

    missing = []
    for dir_path, abs_path in required_dirs.items():
        if not abs_path.exists():
            missing.append(dir_path)
    
    if missing:
        print(f"✗ Missing directories: {', '.join(missing)}")
        return False
    
    print("✓ Project structure OK")
    return True

def main():
    print("="*60)
    print("CARE Bot Setup Verification")
    print("="*60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Project Structure", check_structure),
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("Data Files", check_data_directory),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        results.append(check_func())
        print()
    
    print("="*60)
    if all(results):
        print("✓ All checks passed! You're ready to run CARE Bot")
        print("\nNext steps:")
        print("  python main.py")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print("\nQuick fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Set up .env: cp .env.example .env")
        print("  3. Add API key to .env file")
        print("  4. Place PDFs in data/raw/")
    print("="*60)
    
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
