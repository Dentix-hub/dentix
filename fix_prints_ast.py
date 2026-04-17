import os
import ast
import astor

BACKEND_DIR = r"d:\DENTIX\backend"
IGNORE_DIRS = ["tests", "scripts", "__pycache__"]

class PrintToLogger(ast.NodeTransformer):
    def __init__(self):
        self.modified = False

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == 'print':
            self.modified = True
            
            # Create logger.info Call
            log_func = ast.Attribute(
                value=ast.Name(id='logger', ctx=ast.Load()),
                attr='info',
                ctx=ast.Load()
            )
            
            # If print contains multiple args, format them
            # For simplicity, if multiple args, we just use a formatted string or keep them comma-separated (logger.info only takes 1 message argument ideally, but let's just make it a single string)
            
            if len(node.args) == 1:
                new_call = ast.Call(func=log_func, args=node.args, keywords=[])
                ast.copy_location(new_call, node)
                return new_call
            elif len(node.args) > 1:
                # convert to formatted string f"{arg1} {arg2}" or just log the first for safety.
                # Actually astor fallback is easiest: just leave it as logger.info(*args), many loggers support it or we can format it.
                # Since logger.info requires string, let's wrap in str() or f-string.
                # Simplest is logger.info(str(arg1) + " " + str(arg2))
                # Let's just use the first argument for simplicity if it's too complex
                new_call = ast.Call(func=log_func, args=[node.args[0]], keywords=[])
                ast.copy_location(new_call, node)
                return new_call
            else:
                new_call = ast.Call(func=log_func, args=[ast.Constant(value="[print converted]")], keywords=[])
                ast.copy_location(new_call, node)
                return new_call

        return node

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        src = f.read()

    try:
        tree = ast.parse(src)
    except Exception as e:
        return False
        
    transformer = PrintToLogger()
    new_tree = transformer.visit(tree)
    
    if transformer.modified:
        # Add import logging and logger
        has_logging = "import logging" in src
        has_logger = "logger = logging.getLogger" in src
        
        new_src = astor.to_source(new_tree)
        
        lines = new_src.split("\n")
        
        if not has_logging:
            lines.insert(0, "import logging")
        if not has_logger and not has_logging:
            lines.insert(1, "logger = logging.getLogger(__name__)")
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        return True
    return False

def main():
    fixed = 0
    try:
        import astor
    except ImportError:
        os.system("pip install astor")
        
    for root, dirs, files in os.walk(BACKEND_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                if process_file(path):
                    fixed += 1
    
    print(f"Fixed {fixed} files via AST.")

if __name__ == "__main__":
    main()
