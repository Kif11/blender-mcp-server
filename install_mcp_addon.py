"""
Blender MCP Server Quick Install
Run this in Blender's Text Editor to install the MCP Server panel:
"""

import bpy
import sys
import os

def install_mcp_panel():
    """Install the MCP Server panel into Blender"""
    
    python_dir = os.path.join(os.path.expanduser("~"), "dev", "blender-mcp-server", "python")
    
    if not os.path.exists(python_dir):
        print(f"Creating directory: {python_dir}")
        os.makedirs(python_dir)
    
    script_content = '''"""
Blender MCP Server Addon - Auto-generated
"""

import bpy
import sys
import os
import threading
import http.server
import json
from io import StringIO

bl_info = {
    "name": "MCP Server",
    "author": "MCP Tools",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "N Panel > MCP Server",
    "description": "Start/Stop MCP server for AI integration",
    "category": "Development",
}


class MCP_PT_panel(bpy.types.Panel):
    bl_label = "MCP Server"
    bl_idname = "MCP_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MCP Server"

    def draw(self, context):
        layout = self.layout

        if hasattr(bpy.app, "driver_namespace") and "blender_mcp_server" in bpy.app.driver_namespace:
            server_info = bpy.app.driver_namespace.get("blender_mcp_server")
            if server_info and isinstance(server_info, dict):
                thread = server_info.get("thread")
                if thread and thread.is_alive():
                    layout.label(text="Status: Running", icon="PLAY")
                    layout.operator("mcp.stop_server", icon="STOP")
                    layout.label(text=f"Port: {server_info.get('port', 9877)}")
                    return

        layout.label(text="Status: Stopped", icon="PAUSE")
        layout.operator("mcp.start_server", icon="PLAY")


class MCP_OT_start_server(bpy.types.Operator):
    bl_idname = "mcp.start_server"
    bl_label = "Start MCP Server"
    bl_options = {"REGISTER"}

    def execute(self, context):
        addon_dir = "''' + python_dir.replace("\\", "\\\\") + '''"
        rpc_path = os.path.join(addon_dir, "blender_rpc_service.py")

        if not os.path.exists(rpc_path):
            self.report({"ERROR"}, f"RPC service not found at {rpc_path}")
            return {"CANCELLED"}

        if rpc_path not in sys.path:
            sys.path.insert(0, addon_dir)

        import importlib.util
        spec = importlib.util.spec_from_file_location("blender_rpc_service", rpc_path)
        rpc_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rpc_module)

        if not hasattr(bpy.app, "driver_namespace"):
            bpy.app.driver_namespace = {{}}

        bpy.app.driver_namespace["blender_mcp_server"] = rpc_module.start_rpc_server_thread(port=9877)
        self.report({"INFO"}, "MCP Server started on port 9877")
        return {{"FINISHED"}}


class MCP_OT_stop_server(bpy.types.Operator):
    bl_idname = "mcp.stop_server"
    bl_label = "Stop MCP Server"
    bl_options = {{"REGISTER"}}

    def execute(self, context):
        if not hasattr(bpy.app, "driver_namespace"):
            self.report({{"WARNING"}}, "No MCP server found")
            return {{"CANCELLED"}}

        server_info = bpy.app.driver_namespace.get("blender_mcp_server")
        if not server_info:
            self.report({{"WARNING"}}, "No MCP server found")
            return {{"CANCELLED"}}

        import importlib.util
        addon_dir = "''' + python_dir.replace("\\", "\\\\") + '''"
        rpc_path = os.path.join(addon_dir, "blender_rpc_service.py")
        
        import importlib.util
        spec = importlib.util.spec_from_file_location("blender_rpc_service", rpc_path)
        rpc_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rpc_module)
        
        rpc_module.stop_rpc_server(server_info)

        del bpy.app.driver_namespace["blender_mcp_server"]
        self.report({{"INFO"}}, "MCP Server stopped")
        return {{"FINISHED"}}


classes = [
    MCP_PT_panel,
    MCP_OT_start_server,
    MCP_OT_stop_server,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
'''
    
    script_path = os.path.join(python_dir, "mcp_addon.py")
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    print(f"Addon script saved to: {script_path}")
    
    try:
        exec(open(script_path).read().format(python_dir.replace("\\", "\\\\")))
        print("MCP Server panel installed successfully!")
        print(f"Find it in the N Panel (sidebar) in the 3D View")
    except Exception as e:
        print(f"To complete installation, enable the addon in Preferences:")
        print(f"1. Edit > Preferences > Add-ons")
        print(f"2. Click 'Install' and select: {script_path}")
        print(f"3. Enable the addon")
        print(f"Error: {e}")


if __name__ == "__main__":
    install_mcp_panel()