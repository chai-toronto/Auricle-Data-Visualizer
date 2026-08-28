#!/usr/bin/env python3
import ast

files = [
    'src/main_window.py',
    'src/widgets/annotation_panel.py',
    'src/widgets/spectrogram_widget.py'
]

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        print(f'{filepath}: PASS')
    except SyntaxError as e:
        print(f'{filepath}: FAIL - Line {e.lineno}: {e.msg}')
        if e.text:
            print(f'  {e.text.rstrip()}')
    except Exception as e:
        print(f'{filepath}: ERROR - {type(e).__name__}: {e}')
