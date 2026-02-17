#!/usr/bin/env python3
"""
CARLA SEAL Visualization - System Verification Script
Run this to check if everything is set up correctly
"""

import sys
import subprocess
import os
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_python():
    """Check Python version"""
    print("✓ Python Version Check")
    version = sys.version.split()[0]
    major, minor = map(int, version.split('.')[:2])
    
    if major >= 3 and minor >= 7:
        print(f"  ✅ Python {version} (Required: 3.7+)")
        return True
    else:
        print(f"  ❌ Python {version} (Required: 3.7+)")
        return False

def check_file(filename):
    """Check if a file exists"""
    path = Path(__file__).parent / filename
    if path.exists():
        size = path.stat().st_size
        print(f"  ✅ {filename} ({size:,} bytes)")
        return True
    else:
        print(f"  ❌ {filename} - NOT FOUND")
        return False

def check_module(module_name):
    """Check if a Python module is installed"""
    try:
        __import__(module_name)
        print(f"  ✅ {module_name}")
        return True
    except ImportError:
        print(f"  ❌ {module_name} - NOT INSTALLED")
        return False

def check_port(port=5000):
    """Check if port is available"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result != 0:
            print(f"  ✅ Port {port} is available")
            return True
        else:
            print(f"  ⚠️  Port {port} appears to be in use")
            print(f"      Try: netstat -ano | findstr :{port}  (Windows)")
            print(f"      Or:  lsof -i :{port}  (Mac/Linux)")
            return False
    except Exception as e:
        print(f"  ⚠️  Could not check port: {e}")
        return True

def test_import():
    """Test if server can start"""
    print("🔍 Module Import Test")
    try:
        import flask
        print(f"  ✅ Flask {flask.__version__}")
        return True
    except ImportError as e:
        print(f"  ❌ {e}")
        return False

def run_tests():
    """Run all verification tests"""
    print_header("CARLA SEAL Visualization System Check")
    
    tests_passed = 0
    tests_total = 0
    
    # Python version
    print_header("1. Python Environment")
    tests_total += 1
    if check_python():
        tests_passed += 1
    
    # Required files
    print_header("2. Required Files")
    required_files = [
        'unified_visualization.html',
        'unified_server_simple.py',
        'start_visualization.bat',
        'start_visualization.sh'
    ]
    
    for filename in required_files:
        tests_total += 1
        if check_file(filename):
            tests_passed += 1
    
    # Python modules
    print_header("3. Python Dependencies")
    required_modules = [
        'flask',
        'flask_cors'
    ]
    
    for module in required_modules:
        tests_total += 1
        if check_module(module):
            tests_passed += 1
        else:
            print(f"\n  💡 Install with: pip install {module}")
    
    # Module imports
    print_header("4. Imports Test")
    tests_total += 1
    if test_import():
        tests_passed += 1
    
    # Port availability
    print_header("5. Port Availability")
    tests_total += 1
    if check_port(5000):
        tests_passed += 1
    
    # Summary
    print_header("Summary")
    print(f"Tests Passed: {tests_passed}/{tests_total}\n")
    
    if tests_passed == tests_total:
        print("✅ All checks passed! You're ready to go.\n")
        print("💡 To start:")
        print("   Windows: start_visualization.bat")
        print("   Linux/Mac: ./start_visualization.sh")
        print("   Or: python unified_server_simple.py")
        print("\n👉 Then open: http://localhost:5000\n")
        return True
    else:
        print(f"⚠️  {tests_total - tests_passed} issues found:")
        print("\n💡 Common fixes:")
        print("   1. Missing files? Make sure all files are in the same directory")
        print("   2. Missing Flask? Run: pip install flask flask-cors")
        print("   3. Port in use? Change port in unified_server_simple.py")
        print("\n📖 See VISUALIZATION_SETUP.md for detailed help\n")
        return False

if __name__ == '__main__':
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Check cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
