#!/usr/bin/env python
"""Test syntax of timeseries_widget.py"""
import sys
import ast

try:
    with open('src/widgets/timeseries_widget.py', 'r', encoding='utf-8') as f:
        code = f.read()
    ast.parse(code)
    print("✓ Syntax is valid!")
    sys.exit(0)
except SyntaxError as e:
    print(f"✗ Syntax error at line {e.lineno}: {e.msg}")
    if e.text:
        print(f"  {e.text}")
        if e.offset:
            print(f"  {' ' * (e.offset - 1)}^")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
