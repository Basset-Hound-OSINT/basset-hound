"""
Basset Hound MCP Server

FastMCP server providing tools for entity relationship management in Basset Hound.
Implements entity CRUD, relationship management, search, project management, reports,
and dynamic schema introspection based on data_config.yaml.

This is the main entry point. All tools are organized in the tools/ directory.
"""

from mcp.server.fastmcp import FastMCP

from .tools import register_all_tools

# Initialize FastMCP server
mcp = FastMCP("basset-hound")

# Register all tool modules
register_all_tools(mcp)


# =============================================================================
# Server Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
