#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run([sys.executable, 'test_load_dialog_comprehensive.py'], 
                       capture_output=True, text=True, cwd='C:\\Users\\Ken_User\\Desktop\\Visualization_Tool\\data_visualization_tool')
print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn Code: {result.returncode}")
