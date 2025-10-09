import sys
import os
from pathlib import Path

# Add to your existing CeronaError and other classes...

class ModuleCache:
    """Cache for imported modules to avoid re-execution"""
    def __init__(self):
        self.modules = {}
    
    def get(self, module_path):
        return self.modules.get(module_path)
    
    def set(self, module_path, exports):
        self.modules[module_path] = exports

# Global module cache
_module_cache = ModuleCache()

def resolve_import_path(import_name, current_file_dir):
    """
    Resolve import name to file path.
    
    Search order:
    1. Relative to current file
    2. CERONA_PATH directories
    3. Current working directory
    """
    # Convert dot notation to path: mypackage.subpkg.module -> mypackage/subpkg/module.cerona
    parts = import_name.split('.')
    relative_path = os.path.join(*parts) + '.cerona'
    
    # Search paths
    search_paths = [current_file_dir]
    
    # Add CERONA_PATH
    if 'CERONA_PATH' in os.environ:
        cerona_paths = os.environ['CERONA_PATH'].split(os.pathsep)
        search_paths.extend(cerona_paths)
    
    # Add current working directory
    search_paths.append(os.getcwd())
    
    # Search for the file
    for search_dir in search_paths:
        full_path = os.path.join(search_dir, relative_path)
        if os.path.isfile(full_path):
            return os.path.abspath(full_path)
    
    return None

def import_module(import_name, current_file_dir, line_num=None, original_line=None):
    """
    Import a Cerona module and return its exported namespace.
    
    Returns a dict of exported variables, functions, and classes.
    """
    # Resolve the import path
    module_path = resolve_import_path(import_name, current_file_dir)
    
    if not module_path:
        raise CeronaError(
            f"module '{import_name}' not found",
            line_num,
            original_line
        )
    
    # Check cache
    cached = _module_cache.get(module_path)
    if cached is not None:
        return cached
    
    # Read and execute the module
    try:
        with open(module_path, 'r') as f:
            module_code = f.read()
    except IOError as e:
        raise CeronaError(
            f"failed to read module '{import_name}': {e}",
            line_num,
            original_line
        )
    
    # Execute module in isolated scope
    module_dir = os.path.dirname(module_path)
    module_exports = execute_module(module_code, module_path, module_dir)
    
    # Cache the result
    _module_cache.set(module_path, module_exports)
    
    return module_exports

def execute_module(code, filename, file_dir):
    """
    Execute a module and return its exported namespace.
    Returns dict with variables, functions, and classes.
    """
    # Create isolated scope for the module
    module_scope = {
        '__file__': filename,
        '__dir__': file_dir,
    }
    
    # Use a modified version of ifs() that returns the scope
    # You'll need to refactor ifs() to accept and return scope
    from cerona.main import ifs_with_scope  # You'll create this
    
    ifs_with_scope(code, module_scope, filename)
    
    # Return exported items (everything except builtins starting with __)
    exports = {
        k: v for k, v in module_scope.items() 
        if not k.startswith('__')
    }
    
    return exports


# Add these to your execute_single_command function:

def handle_import_command(i, variables, line_num, original_line, current_file_dir):
    """
    Handle import statements:
    - import mypackage.module
    - import mypackage.module as alias
    - from mypackage.module import func1 func2
    """
    
    if len(i) < 2:
        raise CeronaError(
            "import requires module name",
            line_num,
            original_line
        )
    
    # Case 1: from X import Y Z
    if i[0] == "from":
        if len(i) < 4 or i[2] != "import":
            raise CeronaError(
                "invalid from-import syntax (expected: from MODULE import ITEM1 ITEM2 ...)",
                line_num,
                original_line
            )
        
        module_name = i[1]
        items_to_import = i[3:]
        
        # Import the module
        module_exports = import_module(module_name, current_file_dir, line_num, original_line)
        
        # Import specific items
        for item in items_to_import:
            if item not in module_exports:
                raise CeronaError(
                    f"module '{module_name}' has no attribute '{item}'",
                    line_num,
                    original_line
                )
            variables[item] = module_exports[item]
    
    # Case 2: import X as Y
    elif len(i) >= 4 and i[2] == "as":
        module_name = i[1]
        alias = i[3]
        
        module_exports = import_module(module_name, current_file_dir, line_num, original_line)
        
        # Store as namespace object
        variables[alias] = module_exports
    
    # Case 3: import X
    else:
        module_name = i[1]
        
        module_exports = import_module(module_name, current_file_dir, line_num, original_line)
        
        # Store with last part of module name
        # e.g., import mypackage.utils -> creates 'utils' variable
        alias = module_name.split('.')[-1]
        variables[alias] = module_exports


# Update your main ifs() function to track current file directory:

def ifs(lines, filename="<input>", file_dir=None):
    """
    Main interpreter function - modified to support imports
    """
    if file_dir is None:
        if filename == "<input>":
            file_dir = os.getcwd()
        else:
            file_dir = os.path.dirname(os.path.abspath(filename))
    
    variables = {
        '__file__': filename,
        '__dir__': file_dir,
    }
    functions = {}
    classes = {}
    objects = {}
    
    # ... rest of your existing code ...
    
    def execute_single_command(line_num, i, variables, all_commands):
        # Add this case before your other command handlers:
        
        if i[0] in ["import", "from"]:
            handle_import_command(i, variables, line_num, 
                                original_lines[line_num - 1] if line_num <= len(original_lines) else None,
                                file_dir)
            return
        
        # ... rest of your existing command handling ...


# Helper to create ifs_with_scope for module execution:
def ifs_with_scope(lines, initial_scope, filename="<input>"):
    """Execute code with an initial scope and return the modified scope"""
    # This is a version of ifs() that accepts and modifies a scope dict
    # You'll refactor your existing ifs() to support this
    pass
