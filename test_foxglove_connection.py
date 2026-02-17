#!/usr/bin/env python3
"""
Foxglove Connection Diagnostics
Checks if all components are running correctly
"""

import socket
import sys
import time

def check_port(host, port, timeout=1):
    """Check if a port is accepting connections"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    print("\n" + "="*70)
    print("  🔍 CARLA Foxglove Connection Diagnostics")
    print("="*70 + "\n")
    
    ports = {
        2000: "CARLA Simulator",
        8001: "HTTP Server (HTML)",
        8766: "Foxglove WebSocket"
    }
    
    print("  Checking ports...\n")
    
    all_good = True
    for port, name in ports.items():
        if check_port('localhost', port):
            print(f"  ✅ {name:30} (:{port}) - RUNNING")
        else:
            print(f"  ❌ {name:30} (:{port}) - NOT RUNNING")
            all_good = False
    
    print("\n" + "-"*70)
    
    if all_good:
        print("\n  ✅ All services running! The visualization should work.\n")
        print("  If you still see 'Connecting...':")
        print("    1. Wait 2-3 seconds for sensors to warm up")
        print("    2. Check browser console (F12) for errors")
        print("    3. Refresh page (Ctrl+R)")
        print("\n")
    else:
        print("\n  ❌ Some services are not running:\n")
        
        if not check_port('localhost', 2000):
            print("  🔴 CARLA is not running!")
            print("     Start CARLA with:")
            print("     → CarlaUE4.exe -windowed -carla-port=2000\n")
        
        if not check_port('localhost', 8766):
            print("  🔴 Foxglove server is not running!")
            print("     Start it with:")
            print("     → python foxglove_server.py\n")
        
        if not check_port('localhost', 8001):
            print("  🔴 HTTP server is not running!")
            print("     Start it with:")
            print("     → python start_foxglove.py\n")
    
    print("="*70 + "\n")
    
    return 0 if all_good else 1

if __name__ == '__main__':
    sys.exit(main())
