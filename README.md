# Blender MCP Server

Control Blender from AI assistants via the Model Context Protocol (MCP).

## What It Does

Allows MCP-compatible AI tools (like OpenCode, Claude Desktop, etc.) to:
- Execute Python code in Blender with full `bpy` module access
- Query scene information (objects, collections, frame range, etc.)
- Create and manipulate objects programmatically

## Install

### 1. Clone this repo
```bash
cd ~/dev/
git clone https://github.com/YOUR_USERNAME/blender-mcp-server
```

### 2. Create Python venv and install dependencies
```bash
cd blender-mcp-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 3. Enable the addon in Blender

**Option A - Quick Install:**
1. Open Blender
2. Go to Text Editor > Open > select `install_mcp_addon.py`
3. Press "Run Script"

**Option B - Standard Addon Install:**
1. Edit > Preferences > Add-ons > Install
2. Select `python/__init__.py`
3. Enable "MCP Server"

### 4. Configure your AI client

**OpenCode** - Edit `~/.config/opencode/opencode.json` and add to the `mcp` section:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "blender": {
      "type": "local",
      "command": [
        "/Users/YOUR_USERNAME/dev/blender-mcp-server/venv/bin/python",
        "/Users/YOUR_USERNAME/dev/blender-mcp-server/python/blender_mcp_server.py"
      ],
      "enabled": true
    }
  }
}
```

**Claude Desktop** (`~/.config/claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "blender": {
      "command": "/Users/YOUR_USERNAME/dev/blender-mcp-server/venv/bin/python",
      "args": [
        "/Users/YOUR_USERNAME/dev/blender-mcp-server/python/blender_mcp_server.py"
      ]
    }
  }
}
```

## Usage

1. **Start Blender** and enable the MCP Server addon
2. **Start your AI client** (OpenCode, Claude Desktop, etc.) and make sure that Blender MCP is enabled
3. **Make a prompt with Blender in mind** to control Blender

### Examples

**Create a cube with a material:**
```
Create a cube and assign a metallic material to it.
```

**Modify geometry:**
```
Select all vertices in the active object and randomize their positions slightly.
```

## Available Tools

- **`execute_python`** - Run arbitrary Python code with `bpy` module access
- **`get_scene_info`** - Get blend file path, frame range, selected objects, FPS, etc.
- **`get_collections`** - Get all collections with object counts
- **`get_objects`** - Get objects with transforms, modifiers, constraints
- **`get_context_as_mermaid`** - Visualize node trees or collections as diagrams
- **`get_node_errors`** - Check node tree errors

## Requirements

- Blender 4.2+ (tested on macOS)
- Python 3.11+
- MCP-compatible AI client

## Architecture

```
AI Client ←→ MCP Server ←→ HTTP ←→ RPC Service ←→ Blender
          stdio      (venv)    :9877   (inside Blender)
```

- **`blender_mcp_server.py`** - Runs outside Blender in venv, handles MCP protocol
- **`blender_rpc_service.py`** - Runs inside Blender, executes code with `bpy` module access

Uses HTTP bridge because Blender's Python environment runs in a subprocess.