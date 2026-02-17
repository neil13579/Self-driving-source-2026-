#!/usr/bin/env python3
"""
CARLA Visualization System Diagnostic Tool
Checks all components are working correctly
"""

import socket
import subprocess
import sys
import os
import json
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def check_port(host, port, name):
    """Check if a port is accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"{Colors.GREEN}✅{Colors.RESET} {name} (:{port}) - OPEN")
            return True
        else:
            print(f"{Colors.RED}❌{Colors.RESET} {name} (:{port}) - NOT RESPONDING")
            return False
    except Exception as e:
        print(f"{Colors.RED}❌{Colors.RESET} {name} - ERROR: {e}")
        return False

def check_file(filepath, name):
    """Check if a file exists"""
    if Path(filepath).exists():
        print(f"{Colors.GREEN}✅{Colors.RESET} {name} - Found")
        return True
    else:
        print(f"{Colors.RED}❌{Colors.RESET} {name} - MISSING!")
        return False

def check_import(module_name, display_name):
    """Check if a Python module can be imported"""
    try:
        __import__(module_name)
        print(f"{Colors.GREEN}✅{Colors.RESET} {display_name} - Installed")
        return True
    except ImportError:
        print(f"{Colors.RED}❌{Colors.RESET} {display_name} - NOT INSTALLED")
        return False

def main():
    print("\n" + "="*70)
    print(f"{Colors.BLUE}🔍 CARLA Visualization System Diagnostic{Colors.RESET}")
    print("="*70 + "\n")
    
    all_good = True
    
    # === PYTHON DEPENDENCIES ===
    print(f"{Colors.YELLOW}📦 Python Dependencies:{Colors.RESET}")
    deps = [
        ('carla', 'CARLA'),
        ('websockets', 'WebSockets'),
        ('cv2', 'OpenCV'),
        ('numpy', 'NumPy'),
        ('tensorflow', 'TensorFlow'),
        ('asyncio', 'AsyncIO'),
        ('json', 'JSON'),
    ]
    
    for module, display in deps:
        if not check_import(module, display):
            all_good = False
    
    # === FILE STRUCTURE ===
    print(f"\n{Colors.YELLOW}📁 Required Files:{Colors.RESET}")
    files = [
        ('main.py', 'Perception Server'),
        ('index.html', 'Web Visualization'),
        ('serve_web.py', 'HTTP Server'),
        ('carla_vision.py', 'Vision Module'),
        ('ego_spawn.py', 'Ego Spawn Module'),
        ('config.json', 'Configuration'),
    ]
    
    for file, display in files:
        if not check_file(Path(__file__).parent / file, display):
            all_good = False
    
    # === NETWORK CONNECTIVITY ===
    print(f"\n{Colors.YELLOW}🌐 Network Connectivity:{Colors.RESET}")
    
    # Check CARLA
    if check_port('localhost', 2000, 'CARLA Simulator'):
        print("   ℹ️  CARLA is running ✓")
    else:
        print(f"   ⚠️  {Colors.YELLOW}CARLA is NOT running!{Colors.RESET}")
        print(f"   → Start it with: CarlaUE4.exe -windowed -carla-port=2000")
        all_good = False
    
    # Check WebSocket
    if check_port('localhost', 8765, 'WebSocket (main.py)'):
        print("   ℹ️  main.py is running ✓")
    else:
        print(f"   ⚠️  {Colors.YELLOW}main.py is NOT running!{Colors.RESET}")
        print(f"   → Start it with: python main.py")
    
    # Check HTTP Server
    if check_port('localhost', 8000, 'HTTP Server'):
        print("   ℹ️  serve_web.py is running ✓")
    else:
        print(f"   ⚠️  {Colors.YELLOW}serve_web.py is NOT running!{Colors.RESET}")
        print(f"   → Start it with: python serve_web.py")
    
    # === CONFIGURATION ===
    print(f"\n{Colors.YELLOW}⚙️  Configuration:{Colors.RESET}")
    config_path = Path(__file__).parent / 'config' / 'config.json'
    
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            print(f"{Colors.GREEN}✅{Colors.RESET} config.json - Valid")
            
            # Check important settings
            if 'carla' in config:
                print(f"   • CARLA host: {config['carla'].get('host', 'localhost')}")
                print(f"   • CARLA port: {config['carla'].get('port', 2000)}")
        except json.JSONDecodeError:
            print(f"{Colors.RED}❌{Colors.RESET} config.json - Invalid JSON!")
            all_good = False
    else:
        print(f"{Colors.RED}❌{Colors.RESET} config.json - Not found!")
    
    # === SUMMARY ===
    print("\n" + "="*70)
    if all_good:
        print(f"{Colors.GREEN}✅ All checks passed!{Colors.RESET}")
        print("\n📋 Quick Start:")
        print("  1. Make sure CARLA is running on localhost:2000")
        print("  2. Terminal 1: python main.py")
        print("  3. Terminal 2: python serve_web.py")
        print("  4. Open browser: http://localhost:8000/index.html")
        print("\n💡 Open browser DevTools (F12) to see WebSocket debug messages")
    else:
        print(f"{Colors.RED}⚠️  Some checks failed - see above for details{Colors.RESET}")
        print("\n🔧 Common Fixes:")
        print("  • Run 'pip install -r requirements.txt' to install missing packages")
        print("  • Make sure CARLA simulator is running")
        print("  • Check your firewall settings for Python ports")
        print("  • Run this diagnostic again after fixing issues")
    
    print("="*70 + "\n")
    return 0 if all_good else 1

if __name__ == '__main__':
    sys.exit(main())
