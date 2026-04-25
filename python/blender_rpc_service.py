"""
Blender HTTP RPC Service
Runs INSIDE Blender and provides an HTTP API for executing Python code
This runs in Blender's Python environment

IMPORTANT: All bpy operations are scheduled to the main thread via bpy.app.timers
because Blender's API is not thread-safe.
"""

import bpy
import http.server
import json
import sys
import threading
import socket
import queue
from io import StringIO


def _execute_on_main_thread(func, args, kwargs, result_queue):
    """Helper that runs on main thread via timer, then puts result in queue."""
    try:
        result = func(*args, **kwargs)
        result_queue.put(("ok", result))
    except Exception as e:
        import traceback
        result_queue.put(("error", f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"))


def call_on_main_thread(func, args=(), kwargs=None, timeout=10.0):
    """Schedule a function to run on Blender's main thread and wait for the result.
    
    Returns the result dict or raises an exception.
    """
    if kwargs is None:
        kwargs = {}
    result_queue = queue.Queue()

    def timer_callback():
        _execute_on_main_thread(func, args, kwargs, result_queue)
        return None  # don't repeat

    bpy.app.timers.register(timer_callback, first_interval=0.0)

    try:
        status, value = result_queue.get(timeout=timeout)
        if status == "error":
            return {"error": value}
        return value
    except queue.Empty:
        return {"error": f"Timed out after {timeout}s waiting for main thread"}


class BlenderRPCHandler(http.server.BaseHTTPRequestHandler):
    """Handle RPC requests from the MCP server"""

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            request = json.loads(post_data)
            method = request.get('method')
            params = request.get('params', {})

            if method == 'execute_python':
                result = call_on_main_thread(execute_python, (params.get('code', ''),))
            elif method == 'get_scene_info':
                result = call_on_main_thread(get_scene_info)
            elif method == 'get_context_as_mermaid':
                result = call_on_main_thread(get_context_as_mermaid, (params.get('context_path', 'MASTER'),))
            elif method == 'get_node_errors':
                result = call_on_main_thread(get_node_errors, (params.get('context_path', 'MASTER'),))
            elif method == 'get_collections':
                result = call_on_main_thread(get_collections)
            elif method == 'get_objects':
                result = call_on_main_thread(get_objects, (params.get('collection', None),))
            else:
                result = {'error': f'Unknown method: {method}'}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            error_response = {'error': str(e)}
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())


# All bpy operations are standalone functions so they can be called via call_on_main_thread.
# They must NEVER run on the HTTP server thread.

def execute_python(code):
    """Execute Python code in Blender context (must run on main thread)"""
    exec_globals = {"bpy": bpy}
    exec_locals = {}

    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        exec(code, exec_globals, exec_locals)
        output = captured_output.getvalue()
        result = exec_locals.get("_", None)

        return {
            'output': output,
            'result': str(result) if result is not None else None
        }
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        return {
            'error': error_msg,
            'output': captured_output.getvalue()
        }
    finally:
        sys.stdout = old_stdout


def get_scene_info():
    """Get current scene information (must run on main thread)"""
    try:
        scene = bpy.context.scene
        blend_file = bpy.data.filepath
        blend_name = blend_file.split('/')[-1] if blend_file else "Untitled"
        active_obj = bpy.context.active_object if hasattr(bpy.context, 'active_object') and bpy.context.active_object else None
        return {
            "blend_file": blend_file,
            "blend_name": blend_name,
            "is_saved": bool(blend_file),
            "frame_range": {
                "start": scene.frame_start,
                "end": scene.frame_end,
                "current": scene.frame_current
            },
            "fps": scene.render.fps,
            "selected_objects": [obj.name for obj in bpy.context.selected_editable_objects] if hasattr(bpy.context, 'selected_editable_objects') else [],
            "active_object": active_obj.name if active_obj else None,
            "pwd": bpy.context.collection.name if hasattr(bpy.context, 'collection') and bpy.context.collection else "Master Collection",
            "blender_version": bpy.app.version_string,
        }
    except Exception as e:
        import traceback
        return {
            'error': f"Failed to get scene info: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        }


def get_context_as_mermaid(context_path):
    """Get Blender node tree or collection as Mermaid diagram (must run on main thread)"""
    try:
        if context_path == 'MASTER':
            return _get_collection_mermaid(bpy.context.scene.collection)

        node_tree = bpy.data.node_groups.get(context_path)
        if node_tree:
            return _get_node_tree_mermaid(node_tree)

        collection = bpy.data.collections.get(context_path)
        if collection:
            return _get_collection_mermaid(collection)

        return {'error': f'Context not found: {context_path}'}

    except Exception as e:
        import traceback
        return {
            'error': f"Failed to generate mermaid diagram: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        }


def _get_node_tree_mermaid(node_tree):
    """Generate mermaid diagram for a Blender node tree"""
    lines = ["graph TD"]

    nodes = list(node_tree.nodes)
    if not nodes:
        return {'result': f"graph TD\n  empty[No nodes in {node_tree.name}]"}

    declared_nodes = set()

    for node in nodes:
        node_id = node.name.replace(" ", "_").replace(".", "_")
        node_type = node.bl_idname

        lines.append(f'  {node_id}[{node_type}]')

        for input_socket in node.inputs:
            if input_socket.is_linked:
                from_node = input_socket.links[0].from_node
                from_id = from_node.name.replace(" ", "_").replace(".", "_")
                lines.append(f"  {from_id} --> {node_id}")
                declared_nodes.add(from_id)
                declared_nodes.add(node_id)

    for node in nodes:
        if node.name.replace(" ", "_").replace(".", "_") not in declared_nodes:
            node_id = node.name.replace(" ", "_").replace(".", "_")
            node_type = node.bl_idname
            lines.append(f'  {node_id}[{node_type}]')

    mermaid_diagram = "\n".join(lines)
    return {'result': mermaid_diagram, 'context_type': 'node_tree', 'context_name': node_tree.name}


def _get_collection_mermaid(collection):
    """Generate mermaid diagram for a collection showing objects and hierarchy"""
    lines = ["graph TD"]

    collection_name = collection.name.replace(" ", "_").replace(".", "_")
    lines.append(f'  {collection_name}[📁 {collection.name}]')

    for obj in collection.objects:
        obj_id = obj.name.replace(" ", "_").replace(".", "_")
        obj_type = obj.type
        lines.append(f'  {obj_id}[{obj_type}: {obj.name}]')
        lines.append(f'  {collection_name} --> {obj_id}')

        if obj.children:
            for child in obj.children:
                child_id = child.name.replace(" ", "_").replace(".", "_")
                lines.append(f'  {obj_id} --> {child_id}')

    mermaid_diagram = "\n".join(lines)
    return {'result': mermaid_diagram, 'context_type': 'collection', 'context_name': collection.name}


def get_node_errors(context_path='MASTER'):
    """Get all node errors for a specified Blender node tree (must run on main thread)"""

    if context_path == 'MASTER':
        node_tree_names = [ng.name for ng in bpy.data.node_groups]
        all_errors = []

        for nt_name in node_tree_names:
            errors = _check_node_tree_errors(nt_name)
            all_errors.extend(errors)

        return {'result': {
            'context': context_path,
            'total_errors': len(all_errors),
            'nodes_with_errors': all_errors
        }}

    errors = _check_node_tree_errors(context_path)
    return {'result': {
        'context': context_path,
        'total_errors': len(errors),
        'nodes_with_errors': errors
    }}


def _check_node_tree_errors(node_tree_name):
    """Check errors in a single node tree"""
    node_tree = bpy.data.node_groups.get(node_tree_name)
    if not node_tree:
        return []

    nodes_with_errors = []

    for node in node_tree.nodes:
        errors = []

        if hasattr(node, 'error_message') and node.error_message:
            errors.append(node.error_message)

        if hasattr(node, 'inputs'):
            for socket in node.inputs:
                if socket.is_linked:
                    try:
                        from_socket = socket.links[0].from_socket
                        if not from_socket.is_linked:
                            errors.append(f"Unconnected input: {socket.name}")
                    except:
                        pass

        if errors:
            nodes_with_errors.append({
                'name': node.name,
                'type': node.bl_idname,
                'errors': errors
            })

    return nodes_with_errors


def get_collections():
    """Get all collections in the scene (must run on main thread)"""
    try:
        collections = []
        for coll in bpy.data.collections:
            collections.append({
                'name': coll.name,
                'object_count': len(coll.objects),
                'children': [c.name for c in coll.children]
            })

        return {'result': collections}
    except Exception as e:
        import traceback
        return {'error': f"Failed to get collections: {str(e)}"}


def get_objects(collection_name=None):
    """Get objects, optionally filtered by collection (must run on main thread)"""
    try:
        objects = []

        if collection_name:
            collection = bpy.data.collections.get(collection_name)
            if not collection:
                return {'error': f'Collection not found: {collection_name}'}
            obj_iter = collection.objects
        else:
            obj_iter = bpy.data.objects

        for obj in obj_iter:
            objects.append({
                'name': obj.name,
                'type': obj.type,
                'location': list(obj.location),
                'rotation': list(obj.rotation_euler),
                'scale': list(obj.scale),
                'parent': obj.parent.name if obj.parent else None,
                'modifiers': [m.name for m in obj.modifiers],
                'constraints': [c.name for c in obj.constraints]
            })

        return {'result': objects}
    except Exception as e:
        import traceback
        return {'error': f"Failed to get objects: {str(e)}"}


class StoppableHTTPServer(http.server.HTTPServer):
    """HTTPServer with proper shutdown support"""

    def __init__(self, *args, **kwargs):
        http.server.HTTPServer.__init__(self, *args, **kwargs)
        self._stop_event = threading.Event()

    def serve_forever_stoppable(self):
        """Serve requests until stop() is called"""
        while not self._stop_event.is_set():
            self.handle_request()

    def stop(self):
        """Stop the server"""
        self._stop_event.set()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.server_address)
            sock.close()
        except:
            pass


def start_rpc_server(port=9877, server_holder=None):
    """Start the HTTP RPC server"""
    server = StoppableHTTPServer(('localhost', port), BlenderRPCHandler)

    if server_holder is not None:
        server_holder['instance'] = server

    print(f"Blender MCP RPC Service started on http://localhost:{port}")
    server.serve_forever_stoppable()
    server.server_close()


def start_rpc_server_thread(port=9877):
    """Start the RPC server in a background thread"""
    server_holder = {}

    thread = threading.Thread(
        target=start_rpc_server,
        args=(port, server_holder),
        daemon=True
    )
    thread.start()

    import time
    time.sleep(0.1)

    return {
        'thread': thread,
        'server_holder': server_holder,
        'port': port
    }


def stop_rpc_server(server_info):
    """Stop the RPC server"""
    if not isinstance(server_info, dict):
        print("Invalid server info")
        return False

    server_holder = server_info.get('server_holder', {})
    server = server_holder.get('instance')

    if server:
        server.stop()

        thread = server_info.get('thread')
        if thread:
            thread.join(timeout=2.0)

        print("MCP RPC Service stopped")
        return True

    print("No active server found")
    return False


if __name__ == "__main__":
    start_rpc_server_thread()
    print("RPC server running in background. Keep this Blender session open.")
