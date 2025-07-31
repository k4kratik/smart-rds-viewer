#!/usr/bin/env python3
"""
Build script for creating binary executable of Smart RDS Viewer
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

    dirs_to_clean = ["build", "dist"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ Removed {dir_name}/")

    # Remove .spec file
    spec_file = "smart-rds-viewer.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"✓ Removed {spec_file}")


def main():
    """Main build process"""
    print("🚀 Smart RDS Viewer Binary Builder")
    print("=" * 40)

    # Check if we're in the right directory
    if not os.path.exists("rds_viewer.py"):
        print("❌ Error: rds_viewer.py not found in current directory")
        print("Please run this script from the project root directory")
        sys.exit(1)

    # Install PyInstaller
    install_pyinstaller()

    # Clean previous builds
    clean_build()

    # Build binary
    binary_path = build_binary()

    if binary_path:
        print("\n🎉 Build completed successfully!")
        print(f"📁 Binary location: {binary_path}")
        print("\n💡 Usage:")
        print(f"   ./dist/smart-rds-viewer")
        if sys.platform == "win32":
            print(f"   .\\dist\\smart-rds-viewer.exe")
        print("\n⚠️  Note: The binary requires AWS credentials to be configured")
        print("   (environment variables, IAM role, or AWS CLI configuration)")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
