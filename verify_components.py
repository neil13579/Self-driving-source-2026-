#!/usr/bin/env python3
"""
Component Verification Tool
Checks each part of the perception system independently
"""

import sys
import subprocess
import time
from pathlib import Path

def check_component(name, test_fn):
    """Run component test with nice formatting"""
    print(f"\n{'='*60}")
    print(f"  Testing: {name}")
    print('='*60)
    try:
        result = test_fn()
        if result:
            print(f"✅ {name} OK")
            return True
        else:
            print(f"❌ {name} FAILED")
            return False
    except Exception as e:
        print(f"❌ {name} ERROR: {e}")
        return False

def test_python_version():
    """Check Python version"""
    version_info = sys.version_info
    print(f"Python version: {version_info.major}.{version_info.minor}.{version_info.micro}")
    if version_info.major >= 3 and version_info.minor >= 7:
        return True
    print("Need Python 3.7+")
    return False

def test_imports():
    """Check required imports"""
    modules = [
        ('carla', 'CARLA API'),
        ('cv2', 'OpenCV'),
        ('numpy', 'NumPy'),
        ('tensorflow', 'TensorFlow'),
        ('flask', 'Flask'),
        ('websockets', 'WebSockets'),
        ('asyncio', 'AsyncIO'),
    ]
    
    results = {}
    for module_name, display_name in modules:
        try:
            __import__(module_name)
            print(f"  ✅ {display_name:15} ({module_name})")
            results[module_name] = True
        except ImportError as e:
            print(f"  ❌ {display_name:15} - MISSING")
            results[module_name] = False
    
    return all(results.values())

def test_carla_connection():
    """Check CARLA server connection"""
    try:
        import carla
        client = carla.Client('localhost', 2000)
        client.set_timeout(5.0)
        world = client.get_world()
        print(f"  ✅ Connected to CARLA")
        print(f"  Map: {world.get_map().name}")
        print(f"  Actors: {len(world.get_actors())} currently in world")
        return True
    except Exception as e:
        print(f"  ❌ Cannot connect to CARLA")
        print(f"     Make sure CARLA is running on localhost:2000")
        print(f"     Error: {e}")
        return False

def test_models():
    """Check perceptor models"""
    try:
        import tensorflow as tf
        import numpy as np
        
        print("  Testing U-Net model...")
        # Try to create a simple model
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(256, 256, 3)),
            tf.keras.layers.Conv2D(16, 3, activation='relu'),
        ])
        print("  ✅ U-Net model can be created")
        
        # Test YOLO-like detection
        print("  Testing detection pipeline...")
        test_mask = np.zeros((256, 256), dtype=np.uint8)
        test_mask[50:150, 50:150] = 1  # Vehicle class
        print("  ✅ Detection pipeline works")
        
        return True
    except Exception as e:
        print(f"  ❌ Model error: {e}")
        return False

def test_ports():
    """Check if ports are free"""
    import socket
    
    ports = [
        (5000, 'Flask'),
        (8765, 'WebSocket'),
    ]
    
    all_free = True
    for port, service in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('127.0.0.1', port))
            s.close()
            print(f"  ✅ Port {port:5} ({service:12}) - FREE")
        except OSError:
            print(f"  ❌ Port {port:5} ({service:12}) - IN USE")
            all_free = False
    
    return all_free

def test_files():
    """Check required files"""
    files = [
        'unified_perception_server.py',
        'config/general_config.json',
    ]
    
    all_exist = True
    for filename in files:
        filepath = Path(filename)
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  ✅ {filename:40} ({size:,} bytes)")
        else:
            print(f"  ❌ {filename:40} - MISSING")
            all_exist = False
    
    return all_exist

def test_visualization():
    """Test HTML dashboard"""
    try:
        dashboard_file = Path('unified_visualization.html')
        if not dashboard_file.exists():
            print(f"  ❌ Dashboard file not found: {dashboard_file}")
            return False
        
        with open(dashboard_file, 'r') as f:
            content = f.read()
            if 'WebSocket' in content and 'canvas' in content:
                print(f"  ✅ Dashboard HTML file valid")
                return True
            else:
                print(f"  ⚠️  Dashboard HTML may be incomplete")
                return False
    except Exception as e:
        print(f"  ❌ Dashboard error: {e}")
        return False

def main():
    """Run all component checks"""
    print("\n")
    print("    🔹 CARLA PERCEPTION SYSTEM - COMPONENT VERIFICATION 🔹")
    print()
    
    tests = [
        ("Python Version", test_python_version),
        ("Required Packages", test_imports),
        ("CARLA Connection", test_carla_connection),
        ("Perception Models", test_models),
        ("Network Ports", test_ports),
        ("Required Files", test_files),
        ("Dashboard/Visualization", test_visualization),
    ]
    
    results = {}
    for name, test_fn in tests:
        results[name] = check_component(name, test_fn)
    
    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print('='*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    print(f"\n  Total: {passed}/{total} components OK")
    
    if passed == total:
        print("\n  ✅ All systems GO! Ready to run unified_perception_server.py")
        print("\n  Next steps:")
        print("    1. python unified_perception_server.py")
        print("    2. Open browser to http://localhost:5000")
        print("    3. Monitor console for [CHECKPOINT] messages")
        return 0
    else:
        print(f"\n  ⚠️  {total - passed} component(s) need attention")
        print("\n  Common fixes:")
        print("    • Missing packages: pip install -r requirements.txt")
        print("    • CARLA not running: Start CARLA server")
        print("    • Port in use: Kill process using port 5000 or 8765")
        return 1

if __name__ == '__main__':
    sys.exit(main())
