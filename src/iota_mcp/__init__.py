"""MCP server for Islands on the Air — group lookup, island search, DXCC mapping"""

from __future__ import annotations

try:
    from importlib.metadata import version

    __version__ = version("iota-mcp")
except Exception:
    __version__ = "0.0.0-dev"
