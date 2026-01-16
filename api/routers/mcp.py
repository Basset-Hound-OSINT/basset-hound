"""
MCP (Model Context Protocol) HTTP Endpoints for Basset Hound.

This module provides HTTP endpoints for MCP tool discovery and execution,
enabling external services (like PalletAI) to dynamically discover and
invoke Basset Hound's MCP tools without hardcoded tool definitions.

Integration Direction:
- PalletAI -> Basset Hound: PalletAI agents can call these endpoints
- Basset Hound -> PalletAI: NOT SUPPORTED (Basset Hound is the source of truth)

Endpoints:
- GET  /mcp/tools           - List all available MCP tools
- GET  /mcp/tools/{name}    - Get specific tool schema
- GET  /mcp/tools?category= - Filter by category
- POST /mcp/execute         - Execute a tool
- POST /mcp/batch           - Execute multiple tools
- POST /mcp/validate        - Validate parameters without execution
- GET  /mcp/health          - MCP service health check
"""

import asyncio
import inspect
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import get_neo4j_handler

logger = logging.getLogger("basset_hound.mcp")

# =============================================================================
# Pydantic Models
# =============================================================================


class MCPToolParameter(BaseModel):
    """Schema for a tool parameter."""
    name: str
    type: str
    description: str = ""
    required: bool = True
    default: Optional[Any] = None


class MCPToolInfo(BaseModel):
    """Schema for tool information."""
    name: str
    description: str
    category: str = "general"
    parameters: List[MCPToolParameter] = Field(default_factory=list)
    inputSchema: Optional[Dict[str, Any]] = None
    returns: str = "dict"


class MCPToolListResponse(BaseModel):
    """Response for listing tools."""
    tools: List[Dict[str, Any]]
    total: int
    categories: List[str]


class MCPExecuteRequest(BaseModel):
    """Request to execute a tool."""
    tool: str = Field(..., description="Name of the tool to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class MCPExecuteResponse(BaseModel):
    """Response from tool execution."""
    success: bool
    tool: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: int


class MCPBatchExecuteRequest(BaseModel):
    """Request to execute multiple tools."""
    tools: List[MCPExecuteRequest]
    parallel: bool = Field(default=True, description="Execute in parallel if True")


class MCPBatchExecuteResponse(BaseModel):
    """Response from batch tool execution."""
    results: List[MCPExecuteResponse]
    total_execution_time_ms: int
    successful: int
    failed: int


class MCPValidateRequest(BaseModel):
    """Request to validate tool parameters."""
    tool: str
    params: Dict[str, Any] = Field(default_factory=dict)


class MCPValidateResponse(BaseModel):
    """Response from parameter validation."""
    valid: bool
    tool: str
    missing_required: List[str] = Field(default_factory=list)
    unknown_params: List[str] = Field(default_factory=list)
    type_errors: List[str] = Field(default_factory=list)


class MCPHealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: str
    tools_available: int
    database: str


# =============================================================================
# Tool Registry - Imports all MCP tools
# =============================================================================

# Import tool modules
from basset_mcp.tools.entities import register_entity_tools
from basset_mcp.tools.projects import register_project_tools
from basset_mcp.tools.relationships import register_relationship_tools
from basset_mcp.tools.search import register_search_tools
from basset_mcp.tools.analysis import register_analysis_tools
from basset_mcp.tools.schema import register_schema_tools
from basset_mcp.tools.orphans import register_orphan_tools
from basset_mcp.tools.provenance import register_provenance_tools
from basset_mcp.tools.auto_linking import register_auto_linking_tools
from basset_mcp.tools.verification import register_verification_tools
from basset_mcp.tools.investigations import register_investigation_tools
from basset_mcp.tools.sock_puppets import register_sock_puppet_tools
from basset_mcp.tools.browser_integration import register_browser_integration_tools
from basset_mcp.tools.file_hashing import register_file_hashing_tools
from basset_mcp.tools.reports import register_report_tools
from basset_mcp.tools.data_management import register_data_management_tools
from basset_mcp.tools.suggestions import register_suggestion_tools
from basset_mcp.tools.linking import register_linking_tools


class ToolRegistry:
    """
    Registry for MCP tools with HTTP exposure.

    This class collects tool metadata from MCP tool modules and provides
    HTTP-accessible methods for tool discovery and execution.
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._tool_functions: Dict[str, callable] = {}
        self._initialized = False

    def initialize(self):
        """Initialize the tool registry by collecting all tools."""
        if self._initialized:
            return

        # Create a mock MCP server to capture tool registrations
        class MockMCP:
            def __init__(self, registry: 'ToolRegistry'):
                self._registry = registry

            def tool(self, name: str = None, description: str = None):
                """Decorator that captures tool metadata."""
                def decorator(func):
                    tool_name = name or func.__name__
                    tool_desc = description or self._extract_description(func)
                    category = self._infer_category(func)
                    params = self._extract_parameters(func)

                    self._registry._tools[tool_name] = {
                        "name": tool_name,
                        "description": tool_desc,
                        "category": category,
                        "parameters": params,
                        "inputSchema": self._build_input_schema(params),
                        "returns": "dict"
                    }
                    self._registry._tool_functions[tool_name] = func
                    return func
                return decorator

            def _extract_description(self, func) -> str:
                """Extract description from docstring."""
                doc = func.__doc__ or ""
                # Get first paragraph
                lines = doc.strip().split('\n\n')[0].split('\n')
                return ' '.join(line.strip() for line in lines if line.strip())

            def _infer_category(self, func) -> str:
                """Infer category from module name."""
                module = func.__module__
                if 'entities' in module:
                    return 'entities'
                elif 'projects' in module:
                    return 'projects'
                elif 'relationships' in module:
                    return 'relationships'
                elif 'search' in module:
                    return 'search'
                elif 'analysis' in module:
                    return 'analysis'
                elif 'schema' in module:
                    return 'schema'
                elif 'orphans' in module:
                    return 'orphans'
                elif 'provenance' in module:
                    return 'provenance'
                elif 'auto_linking' in module:
                    return 'auto_linking'
                elif 'verification' in module:
                    return 'verification'
                elif 'investigations' in module:
                    return 'investigations'
                elif 'sock_puppets' in module:
                    return 'sock_puppets'
                elif 'browser' in module:
                    return 'browser_integration'
                elif 'file_hashing' in module:
                    return 'file_hashing'
                elif 'reports' in module:
                    return 'reports'
                elif 'data_management' in module:
                    return 'data_management'
                elif 'suggestions' in module:
                    return 'suggestions'
                elif 'linking' in module:
                    return 'linking'
                return 'general'

            def _extract_parameters(self, func) -> List[Dict[str, Any]]:
                """Extract parameters from function signature."""
                sig = inspect.signature(func)
                doc = func.__doc__ or ""

                # Parse Args section from docstring
                param_docs = {}
                args_match = re.search(r'Args:\s*\n(.*?)(?:\n\s*\n|\n\s*Returns:|$)', doc, re.DOTALL)
                if args_match:
                    args_text = args_match.group(1)
                    for match in re.finditer(r'(\w+):\s*(.+?)(?=\n\s*\w+:|$)', args_text, re.DOTALL):
                        param_docs[match.group(1)] = match.group(2).strip().replace('\n', ' ')

                params = []
                for name, param in sig.parameters.items():
                    if name in ('self', 'cls'):
                        continue

                    # Get type annotation
                    type_hint = 'any'
                    if param.annotation != inspect.Parameter.empty:
                        type_hint = self._type_to_string(param.annotation)

                    # Check if required
                    required = param.default == inspect.Parameter.empty
                    default = None if required else param.default

                    params.append({
                        "name": name,
                        "type": type_hint,
                        "description": param_docs.get(name, ""),
                        "required": required,
                        "default": default
                    })

                return params

            def _type_to_string(self, type_hint) -> str:
                """Convert type annotation to string."""
                if type_hint is str:
                    return "string"
                elif type_hint is int:
                    return "integer"
                elif type_hint is float:
                    return "number"
                elif type_hint is bool:
                    return "boolean"
                elif type_hint is dict or str(type_hint).startswith('Dict'):
                    return "object"
                elif type_hint is list or str(type_hint).startswith('List'):
                    return "array"
                elif hasattr(type_hint, '__origin__'):  # Generic types
                    origin = getattr(type_hint, '__origin__', None)
                    if origin is dict:
                        return "object"
                    elif origin is list:
                        return "array"
                return "any"

            def _build_input_schema(self, params: List[Dict]) -> Dict[str, Any]:
                """Build JSON Schema from parameters."""
                properties = {}
                required = []

                for param in params:
                    prop = {
                        "type": param["type"],
                        "description": param["description"]
                    }
                    if param["default"] is not None:
                        prop["default"] = param["default"]
                    properties[param["name"]] = prop

                    if param["required"]:
                        required.append(param["name"])

                return {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }

        # Register all tools
        mock_mcp = MockMCP(self)

        try:
            register_entity_tools(mock_mcp)
            register_project_tools(mock_mcp)
            register_relationship_tools(mock_mcp)
            register_search_tools(mock_mcp)
            register_analysis_tools(mock_mcp)
            register_schema_tools(mock_mcp)
            register_orphan_tools(mock_mcp)
            register_provenance_tools(mock_mcp)
            register_auto_linking_tools(mock_mcp)
            register_verification_tools(mock_mcp)
            register_investigation_tools(mock_mcp)
            register_sock_puppet_tools(mock_mcp)
            register_browser_integration_tools(mock_mcp)
            register_file_hashing_tools(mock_mcp)
            register_report_tools(mock_mcp)
            register_data_management_tools(mock_mcp)
            register_suggestion_tools(mock_mcp)
            register_linking_tools(mock_mcp)
        except Exception as e:
            logger.error(f"Error registering tools: {e}")

        self._initialized = True
        logger.info(f"Registered {len(self._tools)} MCP tools")

    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all tools, optionally filtered by category."""
        self.initialize()
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.get("category", "").lower() == category.lower()]

        return tools

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool metadata by name."""
        self.initialize()
        return self._tools.get(name)

    def get_tool_function(self, name: str) -> Optional[callable]:
        """Get tool function by name."""
        self.initialize()
        return self._tool_functions.get(name)

    def get_categories(self) -> List[str]:
        """Get list of all categories."""
        self.initialize()
        return list(set(t.get("category", "general") for t in self._tools.values()))

    def execute_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool by name with given parameters."""
        func = self.get_tool_function(name)
        if not func:
            raise ValueError(f"Tool not found: {name}")

        return func(**params)

    def validate_params(self, name: str, params: Dict[str, Any]) -> MCPValidateResponse:
        """Validate parameters for a tool."""
        tool = self.get_tool(name)
        if not tool:
            return MCPValidateResponse(
                valid=False,
                tool=name,
                missing_required=["TOOL_NOT_FOUND"]
            )

        tool_params = {p["name"]: p for p in tool.get("parameters", [])}

        missing = []
        unknown = []

        # Check for missing required params
        for param_name, param_info in tool_params.items():
            if param_info.get("required") and param_name not in params:
                missing.append(param_name)

        # Check for unknown params
        for param_name in params:
            if param_name not in tool_params:
                unknown.append(param_name)

        return MCPValidateResponse(
            valid=len(missing) == 0,
            tool=name,
            missing_required=missing,
            unknown_params=unknown
        )


# Global registry instance
_tool_registry = ToolRegistry()


# =============================================================================
# FastAPI Router
# =============================================================================

router = APIRouter(
    prefix="/mcp",
    tags=["MCP - Model Context Protocol"],
    responses={
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    }
)


@router.get("/tools", response_model=MCPToolListResponse)
async def list_tools(category: Optional[str] = None) -> Dict[str, Any]:
    """
    List all available MCP tools.

    Optionally filter by category.

    Categories include: entities, projects, relationships, search, analysis,
    schema, orphans, provenance, auto_linking, verification, investigations,
    sock_puppets, browser_integration, file_hashing, reports, data_management,
    suggestions, linking
    """
    try:
        tools = _tool_registry.list_tools(category)
        categories = _tool_registry.get_categories()

        return {
            "tools": tools,
            "total": len(tools),
            "categories": categories
        }
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tools/{tool_name}", response_model=MCPToolInfo)
async def get_tool_info(tool_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific tool.
    """
    tool = _tool_registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}. Use GET /mcp/tools for available tools."
        )
    return tool


@router.post("/execute", response_model=MCPExecuteResponse)
async def execute_tool(request: MCPExecuteRequest) -> Dict[str, Any]:
    """
    Execute an MCP tool with given parameters.
    """
    start_time = time.time()

    tool = _tool_registry.get_tool(request.tool)
    if not tool:
        return MCPExecuteResponse(
            success=False,
            tool=request.tool,
            error=f"Tool not found: {request.tool}",
            execution_time_ms=int((time.time() - start_time) * 1000)
        )

    try:
        result = _tool_registry.execute_tool(request.tool, request.params)

        # Check if result indicates an error
        if isinstance(result, dict) and "error" in result:
            return MCPExecuteResponse(
                success=False,
                tool=request.tool,
                result=None,
                error=result["error"],
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        return MCPExecuteResponse(
            success=True,
            tool=request.tool,
            result=result,
            error=None,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
    except Exception as e:
        logger.error(f"Error executing tool {request.tool}: {e}")
        return MCPExecuteResponse(
            success=False,
            tool=request.tool,
            result=None,
            error=str(e),
            execution_time_ms=int((time.time() - start_time) * 1000)
        )


@router.post("/batch", response_model=MCPBatchExecuteResponse)
async def batch_execute_tools(request: MCPBatchExecuteRequest) -> Dict[str, Any]:
    """
    Execute multiple tools in a single request.

    If parallel=True, tools are executed concurrently.
    If parallel=False, tools are executed sequentially.
    """
    start_time = time.time()
    results = []

    if request.parallel:
        # Execute in parallel
        async def execute_one(req: MCPExecuteRequest):
            return await execute_tool(req)

        tasks = [execute_one(req) for req in request.tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error responses
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                results[i] = MCPExecuteResponse(
                    success=False,
                    tool=request.tools[i].tool,
                    error=str(result),
                    execution_time_ms=0
                )
    else:
        # Execute sequentially
        for req in request.tools:
            result = await execute_tool(req)
            results.append(result)

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return MCPBatchExecuteResponse(
        results=results,
        total_execution_time_ms=int((time.time() - start_time) * 1000),
        successful=successful,
        failed=failed
    )


@router.post("/validate", response_model=MCPValidateResponse)
async def validate_tool_params(request: MCPValidateRequest) -> Dict[str, Any]:
    """
    Validate tool parameters without executing the tool.

    Useful for pre-flight checks before actual execution.
    """
    return _tool_registry.validate_params(request.tool, request.params)


@router.get("/health", response_model=MCPHealthResponse)
async def mcp_health() -> Dict[str, Any]:
    """
    Health check for MCP service.

    Checks database connectivity and tool availability.
    """
    from api.config import get_settings

    settings = get_settings()

    # Check database
    try:
        db = get_neo4j_handler()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Get tool count
    try:
        tools = _tool_registry.list_tools()
        tool_count = len(tools)
    except Exception:
        tool_count = 0

    return MCPHealthResponse(
        status="healthy" if db_status == "connected" and tool_count > 0 else "degraded",
        service="basset-hound-mcp",
        version=settings.app_version,
        timestamp=datetime.now().isoformat(),
        tools_available=tool_count,
        database=db_status
    )
