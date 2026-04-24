#!/usr/bin/env python3
"""
Blender MCP Server
Model Context Protocol server for Blender integration.

Uses HTTP bridge architecture:
- Runs with standard Python (handles MCP protocol)
- Communicates with Blender via HTTP RPC service
"""

import asyncio
import json
import sys
import httpx
from typing import Any

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    import mcp.server.stdio
except ImportError:
    print("Error: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)


class BlenderMCPServerHTTP:
    """MCP Server that connects to Blender via HTTP"""

    def __init__(self, blender_url="http://localhost:9877"):
        self.server = Server("blender-mcp-server")
        self.blender_url = blender_url
        self.http_client = None
        self.setup_handlers()

    def setup_handlers(self):
        """Setup MCP protocol handlers"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="execute_python",
                    description=(
                        "Execute arbitrary Python code within Blender's context. "
                        "Has full access to the 'bpy' module and all Blender APIs. "
                        "Returns the result of the last expression or any print output."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Python code to execute in Blender context"
                            }
                        },
                        "required": ["code"]
                    }
                ),
                Tool(
                    name="get_scene_info",
                    description=(
                        "Get information about the current Blender scene including "
                        "selected objects, current frame, blend file path, and render settings."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_context_as_mermaid",
                    description=(
                        "Get a Blender node tree or collection as a Mermaid diagram. "
                        "Shows node graph structure or collection hierarchy in Mermaid format."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "context_path": {
                                "type": "string",
                                "description": "Node tree name or collection name. Use 'MASTER' for main collection.",
                                "default": "MASTER"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_node_errors",
                    description=(
                        "Get all errors in a specified Blender node tree. "
                        "Optionally check all node trees if context is 'MASTER'."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "context_path": {
                                "type": "string",
                                "description": "Node tree name or 'MASTER' for all trees.",
                                "default": "MASTER"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_collections",
                    description=(
                        "Get all collections in the Blender scene with object counts and hierarchy."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_objects",
                    description=(
                        "Get objects from the scene, optionally filtered by collection. "
                        "Returns object names, types, transforms, modifiers, and constraints."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "collection": {
                                "type": "string",
                                "description": "Optional collection name to filter objects",
                                "default": None
                            }
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls"""

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.blender_url,
                        json={"method": name, "params": arguments}
                    )
                    response.raise_for_status()
                    result = response.json()

                if 'error' in result:
                    return [TextContent(type="text", text=f"Error: {result['error']}")]
                elif 'output' in result and 'result' in result:
                    text = result['output']
                    if result['result']:
                        text += f"\nResult: {result['result']}"
                    return [TextContent(type="text", text=text or "Code executed successfully")]
                elif 'result' in result:
                    return [TextContent(type="text", text=str(result['result']))]
                else:
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except httpx.ConnectError:
                return [TextContent(
                    type="text",
                    text=f"Error: Cannot connect to Blender RPC service at {self.blender_url}\n"
                         f"Make sure Blender is running and the RPC service is started.\n"
                         f"Enable the MCP addon in Blender or run: execfile('path/to/blender_rpc_service.py')"
                )]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def run(self):
        """Run the MCP server using stdio transport"""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point"""
    blender_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9877"

    print(f"Starting Blender MCP Server (HTTP Bridge)", file=sys.stderr)
    print(f"Connecting to Blender RPC at: {blender_url}", file=sys.stderr)

    server = BlenderMCPServerHTTP(blender_url)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()