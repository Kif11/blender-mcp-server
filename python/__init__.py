"""
Blender MCP Server Addon
Install via: Edit > Preferences > Add-ons > Install > select this file
"""

import bpy
import sys
import os

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

        if hasattr(bpy.app, 'driver_namespace') and 'blender_mcp_server' in bpy.app.driver_namespace:
            server_info = bpy.app.driver_namespace.get('blender_mcp_server')
            if server_info and isinstance(server_info, dict):
                thread = server_info.get('thread')
                if thread and thread.is_alive():
                    layout.label(text="Status: Running", icon='PLAY')
                    layout.operator("mcp.stop_server", icon='STOP')
                    layout.label(text=f"Port: {server_info.get('port', 9877)}")
                    return

        layout.label(text="Status: Stopped", icon='PAUSE')
        layout.operator("mcp.start_server", icon='PLAY')


class MCP_OT_start_server(bpy.types.Operator):
    bl_idname = "mcp.start_server"
    bl_label = "Start MCP Server"
    bl_options = {'REGISTER'}

    def execute(self, context):
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        python_dir = addon_dir
        rpc_path = os.path.join(python_dir, 'blender_rpc_service.py')

        if not os.path.exists(rpc_path):
            rpc_path = os.path.join(os.path.expanduser('~'), 'dev', 'blender-mcp-server', 'python', 'blender_rpc_service.py')

        if not os.path.exists(rpc_path):
            self.report({'ERROR'}, f"RPC service not found. Install blender-mcp-server first.")
            return {'CANCELLED'}

        if rpc_path not in sys.path:
            sys.path.insert(0, os.path.dirname(rpc_path))

        from blender_rpc_service import start_rpc_server_thread

        if not hasattr(bpy.app, 'driver_namespace'):
            bpy.app.driver_namespace = {}

        bpy.app.driver_namespace['blender_mcp_server'] = start_rpc_server_thread(port=9877)
        self.report({'INFO'}, "MCP Server started on port 9877")
        return {'FINISHED'}


class MCP_OT_stop_server(bpy.types.Operator):
    bl_idname = "mcp.stop_server"
    bl_label = "Stop MCP Server"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if not hasattr(bpy.app, 'driver_namespace'):
            self.report({'WARNING'}, "No MCP server found")
            return {'CANCELLED'}

        server_info = bpy.app.driver_namespace.get('blender_mcp_server')
        if not server_info:
            self.report({'WARNING'}, "No MCP server found")
            return {'CANCELLED'}

        from blender_rpc_service import stop_rpc_server
        stop_rpc_server(server_info)

        del bpy.app.driver_namespace['blender_mcp_server']
        self.report({'INFO'}, "MCP Server stopped")
        return {'FINISHED'}


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