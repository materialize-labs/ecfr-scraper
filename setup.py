#!/usr/bin/env python3
"""
eCFR Scraper Setup Script
Automated setup for virtual environment and dependencies
"""

import os
import sys
import subprocess
import platform

def run_command(command, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        sys.exit(1)

def main():
    """Main setup function."""
    print("eCFR Scraper - Project Setup")
    print("=" * 40)
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print("Error: Python 3.8+ is required")
        sys.exit(1)
    
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Create virtual environment
    venv_path = "venv"
    if not os.path.exists(venv_path):
        print("\nCreating virtual environment...")
        run_command(f"{sys.executable} -m venv {venv_path}")
    else:
        print("\nVirtual environment already exists")
    
    # Determine activation command based on OS
    if platform.system() == "Windows":
        activate_cmd = f"{venv_path}\\Scripts\\activate"
        pip_cmd = f"{venv_path}\\Scripts\\pip"
        python_cmd = f"{venv_path}\\Scripts\\python"
    else:
        activate_cmd = f"source {venv_path}/bin/activate"
        pip_cmd = f"{venv_path}/bin/pip"
        python_cmd = f"{venv_path}/bin/python"
    
    # Upgrade pip
    print("\nUpgrading pip...")
    run_command(f"{pip_cmd} install --upgrade pip")
    
    # Install requirements
    print("\nInstalling requirements...")
    run_command(f"{pip_cmd} install -r requirements.txt")
    
    # Create directories
    directories = [
        "data",
        "logs",
        "src",
        "tests",
        "config"
    ]
    
    print("\nCreating project directories...")
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created: {directory}/")
    
    print("\n" + "=" * 40)
    print("Setup completed successfully!")
    print("\nTo activate the virtual environment:")
    if platform.system() == "Windows":
        print(f"  {venv_path}\\Scripts\\activate")
    else:
        print(f"  source {venv_path}/bin/activate")
    
    print("\nTo run the scraper:")
    print("  python -m src.main --help")
    
    print("\nTo deactivate the virtual environment:")
    print("  deactivate")

if __name__ == "__main__":
    main()