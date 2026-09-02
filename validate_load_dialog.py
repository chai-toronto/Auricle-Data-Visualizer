import ast
file_path = 'src/widgets/load_dialog.py'
try:
    with open(file_path, 'r') as f:
        code = f.read()
    tree = ast.parse(code)
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    print("=== AST VALIDATION RESULTS ===")
    print(f"File: {file_path}")
    print("Syntax: VALID")
    for cls in classes:
        methods = [n.name for n in cls.body if isinstance(n, ast.FunctionDef)]
        print(f"Class: {cls.name}")
        print(f"Methods: {methods}")
except SyntaxError as e:
    print("=== AST VALIDATION RESULTS ===")
    print(f"File: {file_path}")
    print(f"Syntax: INVALID")
    print(f"Error: {e}")
except Exception as e:
    print("=== AST VALIDATION RESULTS ===")
    print(f"File: {file_path}")
    print(f"Parsing Error: {e}")
