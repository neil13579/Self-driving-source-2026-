#!/usr/bin/env python3
"""
Console Monitor for Perception Server
Watches server output and highlights important checkpoints
Color codes different types of messages for easier debugging
"""

import sys
import subprocess
import re
from pathlib import Path

# Color codes for console output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Standard colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'

def colorize_line(line):
    """Add colors to console output based on checkpoint type"""
    
    # Error messages - RED
    if '[ERROR]' in line or 'Error' in line or 'error' in line or 'ERROR' in line:
        return f"{Colors.BG_RED}{Colors.WHITE}{line}{Colors.RESET}"
    
    # Initialization - BLUE
    if '[INIT-' in line:
        return f"{Colors.BRIGHT_BLUE}{line}{Colors.RESET}"
    
    # Checkpoint progress - CYAN
    if '[CHECKPOINT' in line:
        return f"{Colors.BRIGHT_CYAN}{line}{Colors.RESET}"
    
    # Progress indicators - YELLOW
    if '[PROGRESS]' in line:
        return f"{Colors.BRIGHT_YELLOW}{line}{Colors.RESET}"
    
    # WebSocket events - MAGENTA
    if '[WS-' in line:
        return f"{Colors.BRIGHT_MAGENTA}{line}{Colors.RESET}"
    
    # Frame processing - GREEN
    if '[PROC-' in line or '[FRAME-' in line or '[ENCODE-' in line:
        return f"{Colors.GREEN}{line}{Colors.RESET}"
    
    # Broadcasting - BRIGHT GREEN
    if '[BROADCAST-' in line or '[MESSAGE-' in line:
        return f"{Colors.BRIGHT_GREEN}{line}{Colors.RESET}"
    
    # Flask - BRIGHT YELLOW
    if '[FLASK-' in line:
        return f"{Colors.BRIGHT_YELLOW}{line}{Colors.RESET}"
    
    # Warnings
    if '[WARNING]' in line or '[WARN]' in line:
        return f"{Colors.YELLOW}{line}{Colors.RESET}"
    
    # Normal output
    return line

def extract_checkpoint_type(line):
    """Extract checkpoint type for counting"""
    patterns = {
        'INIT': r'\[INIT-',
        'CHECKPOINT': r'\[CHECKPOINT',
        'PROGRESS': r'\[PROGRESS\]',
        'WS': r'\[WS-',
        'FRAME': r'\[(FRAME|PROC|ENCODE|MESSAGE|BROADCAST)',
        'FLASK': r'\[FLASK-',
        'ERROR': r'\[ERROR\]|ERROR|Error',
    }
    
    for label, pattern in patterns.items():
        if re.search(pattern, line):
            return label
    return 'OTHER'

def main():
    """Run the perception server with colored output"""
    
    print("\n" + "="*70)
    print("  CARLA PERCEPTION SERVER - COLORED DIAGNOSTIC MONITOR")
    print("="*70)
    print("\nColor Legend:")
    print(f"  {Colors.BRIGHT_BLUE}[INIT-X]{Colors.RESET} = Initialization stages")
    print(f"  {Colors.BRIGHT_CYAN}[CHECKPOINT]{Colors.RESET} = Actor spawning")
    print(f"  {Colors.GREEN}[PROC/FRAME/ENCODE]{Colors.RESET} = Data processing")
    print(f"  {Colors.BRIGHT_GREEN}[BROADCAST/MESSAGE]{Colors.RESET} = WebSocket broadcasting")
    print(f"  {Colors.BRIGHT_MAGENTA}[WS-]{Colors.RESET} = WebSocket events")
    print(f"  {Colors.BRIGHT_YELLOW}[FLASK-]{Colors.RESET} = HTTP endpoints")
    print(f"  {Colors.BG_RED}{Colors.WHITE}[ERROR]{Colors.RESET} = Error conditions")
    print("\nPress Ctrl+C to exit server\n")
    print("="*70 + "\n")
    
    try:
        # Start the server
        process = subprocess.Popen(
            [sys.executable, 'unified_perception_server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        checkpoint_counts = {}
        
        # Monitor output
        while True:
            line = process.stdout.readline()
            if not line:
                break  # Process finished
            
            line = line.rstrip('\n')
            
            # Count checkpoint types
            checkpoint_type = extract_checkpoint_type(line)
            checkpoint_counts[checkpoint_type] = checkpoint_counts.get(checkpoint_type, 0) + 1
            
            # Print with colors
            print(colorize_line(line))
        
        # Process finished
        # Process finished
        print("\n" + "="*70)
        print("  SERVER STOPPED")
        print("="*70)
        # Print exit code for diagnostics
        exit_code = process.poll()
        print(f"\nProcess exit code: {exit_code}")
        print("\nCheckpoints Summary:")
        for checkpoint_type, count in sorted(checkpoint_counts.items()):
            print(f"  {checkpoint_type:12}: {count:4}")
        
    except KeyboardInterrupt:
        print("\n" + "="*70)
        print("  SERVER STOPPED BY USER (Ctrl+C)")
        print("="*70)
        print("\nTerminating process...")
        process.terminate()
        process.wait(timeout=5)
        print("Done!")
    
    except Exception as e:
        print(f"\n{Colors.BG_RED}Error: {e}{Colors.RESET}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
