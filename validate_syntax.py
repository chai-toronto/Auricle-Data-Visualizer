#!/usr/bin/env python3
"""Validate Python syntax for three files using AST parsing."""

import ast
import sys

files_to_check = [
    r'src\main_window.py',
    r'src\widgets\annotation_panel.py',
    r'src\widgets\spectrogram_widget.py'
]

print('=' * 70)
print('PYTHON SYNTAX VALIDATION RESULTS (using AST parsing)')
print('=' * 70)

all_valid = True

for filepath in files_to_check:
    print(f'\nFile: {filepath}')
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        ast.parse(source_code, filename=filepath)
        print('Status: VALID')
        
    except SyntaxError as e:
        print('Status: SYNTAX_ERROR')
        print(f'Message: {e.msg}')
        print(f'Location: Line {e.lineno}, Column {e.offset}')
        if e.text:
            print(f'Code: {e.text.rstrip()}')
        all_valid = False
    except FileNotFoundError:
        print('Status: ERROR')
        print('Message: File not found')
        all_valid = False
    except Exception as e:
        print('Status: ERROR')
        print(f'Message: {type(e).__name__}: {str(e)}')
        all_valid = False

print('\n' + '=' * 70)
if all_valid:
    print('RESULT: All files have valid Python syntax')
    sys.exit(0)
else:
    print('RESULT: One or more files have syntax errors')
    sys.exit(1)
