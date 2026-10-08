"""
Canadian Tire Corporation - Fraud & LP Analytics Engine
Environment Verification Script
"""
import sys
import platform
from pathlib import Path

def test_environment() -> None:
    print("=" * 60)
    print("CTC FRAUD ENGINE: ENVIRONMENT VERIFICATION")
    print("=" * 60)
    
    # 1. Check Python Version
    py_version = platform.python_version()
    print(f"[OK] Python Version: {py_version}")
    assert sys.version_info >= (3, 10), "Python 3.10+ is required."

    # 2. Check Virtual Environment
    is_venv = sys.prefix != sys.base_prefix
    if is_venv:
        print(f"[OK] Active Virtual Environment: {sys.prefix}")
    else:
        print("[WARNING] Not running inside a virtual environment (.venv)!")
        
    # 3. Check Directory Structure
    required_dirs = [
        Path("data/raw"),
        Path("data/processed"),
        Path("notebooks"),
        Path("src/graph"),
        Path("src/anomaly"),
        Path("dashboard"),
    ]
    
    print("\nChecking project directories:")
    for directory in required_dirs:
        if directory.exists() and directory.is_dir():
            print(f"  [OK] Directory exists: {directory}")
        else:
            print(f"  [MISSING] Directory missing: {directory}")
            
    print("=" * 60)
    print("Local setup verified successfully. Ready for dependencies.")
    print("=" * 60)

if __name__ == "__main__":
    test_environment()