"""
Blender Scripts Library
Run scripts with: exec(open(run("fog")).read()) or use the run() function below
"""

import os
import bpy

SCRIPTS_DIR = os.path.expanduser("~/resources/blender/scripts")

def run(script_name):
    """Load a script from the scripts directory and return its path."""
    if not script_name.endswith(".py"):
        script_name += ".py"
    return os.path.join(SCRIPTS_DIR, script_name)

def exec_script(script_name):
    """Load and execute a script from the scripts directory."""
    path = run(script_name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Script not found: {path}")
    
    with open(path, 'r') as f:
        code = f.read()
    
    exec(code, {'bpy': bpy, 'os': os})

def reload():
    """Reload all scripts - handy for development."""
    import importlib
    for name in ['fog', 'materials', 'geometry']:
        try:
            exec_script(name)
            print(f"Reloaded: {name}")
        except FileNotFoundError:
            pass