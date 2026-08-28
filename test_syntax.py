#!/usr/bin/env python3
"""Test syntax and attribute order."""
import ast
import sys

files = ['src/main_window.py', 'src/widgets/annotation_panel.py', 'src/widgets/spectrogram_widget.py']

print("=== SYNTAX CHECK ===")
all_ok = True
for fpath in files:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        print(f"✓ {fpath}: OK")
    except SyntaxError as e:
        print(f"✗ {fpath}: SyntaxError at line {e.lineno}: {e.msg}")
        all_ok = False
    except FileNotFoundError:
        print(f"✗ {fpath}: File not found")
        all_ok = False
    except Exception as e:
        print(f"✗ {fpath}: {type(e).__name__}: {e}")
        all_ok = False

print("\n=== MainWindow.__init__ ATTRIBUTE ORDER ===")
try:
    with open('src/main_window.py', 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'MainWindow':
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                    assignments = []
                    for stmt in item.body:
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Attribute):
                                    if target.attr in ['spectrogram_widget', 'spectrogram_annotation_panel']:
                                        assignments.append((target.attr, stmt.lineno))
                    
                    if assignments:
                        print(f"Found {len(assignments)} assignment(s):")
                        for attr, lineno in assignments:
                            print(f"  Line {lineno}: {attr}")
                        
                        # Check order
                        spec_widget_line = None
                        spec_panel_line = None
                        for attr, lineno in assignments:
                            if attr == 'spectrogram_widget':
                                spec_widget_line = lineno
                            elif attr == 'spectrogram_annotation_panel':
                                spec_panel_line = lineno
                        
                        if spec_widget_line and spec_panel_line:
                            if spec_panel_line < spec_widget_line:
                                print(f"\n⚠ ORDER ERROR: spectrogram_annotation_panel (line {spec_panel_line}) initialized BEFORE spectrogram_widget (line {spec_widget_line})")
                                print("   This could cause issues if annotation_panel depends on spectrogram_widget during initialization.")
                            else:
                                print(f"\n✓ Order OK: spectrogram_widget (line {spec_widget_line}) initialized before spectrogram_annotation_panel (line {spec_panel_line})")
                        else:
                            print(f"\n✓ Only one attribute found - no order issue possible")
                    else:
                        print("No attributes found - no issue to check")
                    break
            break
except Exception as e:
    print(f"Error during analysis: {type(e).__name__}: {e}")
    all_ok = False

if all_ok:
    print("\n✓ All checks passed")
    sys.exit(0)
else:
    print("\n✗ Some checks failed")
    sys.exit(1)
