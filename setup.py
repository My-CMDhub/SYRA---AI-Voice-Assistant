#!/usr/bin/env python3
"""
SYRA Setup Script
Helps users set up the SYRA voice assistant with proper dependencies and configuration.
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_os():
    """Check if running on macOS"""
    if platform.system() != "Darwin":
        print("⚠️  SYRA is optimized for macOS due to AppleScript integration")
        print(f"Current OS: {platform.system()}")
        return False
    print(f"✅ Operating System: macOS {platform.mac_ver()[0]}")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("💡 Try running: pip install --upgrade pip")
        return False

def check_microphone():
    """Check if microphone access might be available"""
    print("\n🎤 Checking microphone setup...")
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("✅ Microphone access appears to be working")
            return True
    except ImportError:
        print("❌ SpeechRecognition not installed")
        return False
    except Exception as e:
        print("⚠️  Microphone access issue detected")
        print("📋 To fix microphone permissions:")
        print("1. Open System Preferences → Security & Privacy → Privacy")
        print("2. Click 'Microphone' in the left sidebar")
        print("3. Enable access for Terminal/Python/VS Code")
        return False

def setup_api_key():
    """Guide user through API key setup"""
    print("\n🔑 API Key Setup")
    print("SYRA requires a Mistral AI API key to function.")
    print("🌐 Get your free API key at: https://mistral.ai/")
    
    api_key = input("\nEnter your Mistral AI API key (or press Enter to skip): ").strip()
    
    if api_key:
        # Option 1: Environment variable
        env_choice = input("Set as environment variable? (y/n): ").lower().strip()
        if env_choice == 'y':
            print(f"\n📝 Add this to your shell profile (~/.bashrc, ~/.zshrc):")
            print(f"export MISTRAL_API_KEY='{api_key}'")
            print("\nThen run: source ~/.zshrc (or restart terminal)")
        else:
            # Option 2: Update source code
            print("\n📝 Please update the API key in Assistance_SYRA_Final.py:")
            print(f"MISTRAL_API_KEY = '{api_key}'")
    else:
        print("\n⚠️  API key skipped. You'll need to set it before running SYRA.")
        print("📝 Update MISTRAL_API_KEY in Assistance_SYRA_Final.py")

def create_launch_script():
    """Create a simple launch script"""
    script_content = """#!/bin/bash
# SYRA Launch Script

echo "🚀 Starting SYRA..."
echo "🎙️  Make sure your microphone is ready!"
echo ""

python3 Assistance_SYRA_Final.py
"""
    
    try:
        with open("launch_syra.sh", "w") as f:
            f.write(script_content)
        os.chmod("launch_syra.sh", 0o755)
        print("✅ Created launch script: launch_syra.sh")
        return True
    except Exception as e:
        print(f"⚠️  Could not create launch script: {e}")
        return False

def main():
    """Main setup function"""
    print("🤖 SYRA Setup Assistant")
    print("=" * 50)
    
    # Check system requirements
    if not check_python_version():
        return False
    
    if not check_os():
        response = input("Continue anyway? (y/n): ").lower().strip()
        if response != 'y':
            return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Check microphone
    check_microphone()
    
    # Setup API key
    setup_api_key()
    
    # Create launch script
    create_launch_script()
    
    print("\n🎉 Setup Complete!")
    print("\n🚀 To start SYRA:")
    print("   python3 Assistance_SYRA_Final.py")
    print("   OR")
    print("   ./launch_syra.sh")
    
    print("\n📚 For more help, check README.md")
    print("🐛 For issues, see the Troubleshooting section in README.md")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
