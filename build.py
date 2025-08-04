#!/usr/bin/env python3
"""
Build script for creating binary executable of Smart RDS Viewer
Designed for GitHub Actions and CI/CD workflows
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    try:
        import PyInstaller
        print("✓ PyInstaller already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed successfully")


def build_binary():
    """Build the binary executable"""
    print("🔨 Building Smart RDS Viewer binary...")

    # PyInstaller command with fixes for readchar metadata issue
    cmd = [
        "pyinstaller",
        "--onefile",  # Create a single executable file
        "--name=smart-rds-viewer",  # Name of the binary
        "--distpath=./dist",  # Output directory
        "--workpath=./build",  # Build work directory
        "--specpath=./build",  # Spec file directory
        "--clean",  # Clean cache before building
        "--noconfirm",  # Replace existing files without asking
        "--hidden-import=readchar",  # Explicitly include readchar
        "--hidden-import=importlib.metadata",  # Include metadata handling
        "--collect-all=readchar",  # Collect all readchar files
        "--exclude-module=tkinter",  # Exclude tkinter if not needed
        "--exclude-module=matplotlib",  # Exclude matplotlib if not needed
        "rds_viewer.py",  # Main script
    ]

    try:
        subprocess.check_call(cmd)
        print("✓ Binary built successfully!")

        # Check if binary was created
        binary_path = Path("./dist/smart-rds-viewer")
        if sys.platform == "win32":
            binary_path = Path("./dist/smart-rds-viewer.exe")

        if binary_path.exists():
            print(f"📦 Binary created: {binary_path.absolute()}")
            print(f"📏 Size: {binary_path.stat().st_size / (1024*1024):.1f} MB")
            return str(binary_path.absolute())
        else:
            print("❌ Binary not found in expected location")
            return None

    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return None


def clean_build():
    """Clean build artifacts"""
    print("🧹 Cleaning build artifacts...")
    
    artifacts = ["build", "dist", "*.spec"]
    for pattern in artifacts:
        if pattern.startswith("*"):
            # Handle glob patterns
            import glob
            for file in glob.glob(pattern):
                try:
                    os.remove(file)
                    print(f"  ✓ Removed {file}")
                except OSError:
                    pass
        else:
            # Handle directories
            if os.path.exists(pattern):
                try:
                    shutil.rmtree(pattern)
                    print(f"  ✓ Removed {pattern}/")
                except OSError:
                    pass
    
    print("✓ Cleanup complete")


def validate_environment():
    """Validate the build environment"""
    print("🔍 Validating build environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check for main script
    if not os.path.exists("rds_viewer.py"):
        print("❌ rds_viewer.py not found")
        return False
    
    print("✓ Main script found")
    
    # Check dependencies
    try:
        import boto3
        import rich
        import readchar
        print("✓ All dependencies available")
    except ImportError as e:
        print(f"⚠️  Missing dependency: {e}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    return True


def main():
    """Main build function"""
    print("🚀 Smart RDS Viewer - Build Script")
    print("=" * 40)
    
    # Parse command line arguments
    clean_only = "--clean" in sys.argv
    skip_validation = "--skip-validation" in sys.argv
    
    if clean_only:
        clean_build()
        return
    
    # Validate environment
    if not skip_validation:
        if not validate_environment():
            print("\n❌ Environment validation failed")
            sys.exit(1)
    
    # Clean previous builds
    clean_build()
    
    # Install PyInstaller
    install_pyinstaller()
    
    # Build binary
    binary_path = build_binary()
    
    if binary_path:
        print(f"\n🎉 Build successful!")
        print(f"📦 Binary: {binary_path}")
        print(f"🚀 Ready for distribution!")
    else:
        print(f"\n❌ Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()