"""Discovery-only acceptance shared by TCP-process and Docker smoke runners."""

import asyncio

import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client

TOOL_INPUTS = {
    "list_products": {"page", "per_page", "search", "sku", "status"},
    "get_order": {"order_id"},
    "list_orders": {"page", "per_page", "status", "date"},
    "create_product": {"name", "price", "sku", "status", "stock_status"},
    "update_order_status": {"order_id", "status", "expected_status"},
}


async def discover(url):
    """Never call a tool: inspect SDK metadata only, using real HTTP sockets."""
    async with asyncio.timeout(20):
        async with httpx2.AsyncClient(trust_env=False, timeout=5) as http:
            async with Client(streamable_http_client(url, http_client=http), cache=None) as client:
                tools = (await client.list_tools()).tools
                assert [tool.name for tool in tools] == list(TOOL_INPUTS)
                for index, tool in enumerate(tools):
                    assert set(tool.input_schema["properties"]) == TOOL_INPUTS[tool.name]
                    assert tool.input_schema["additionalProperties"] is False
                    assert tool.output_schema["type"] == "object"
                    assert tool.annotations.read_only_hint == (index < 3)
                    assert tool.annotations.idempotent_hint == (index < 3)
                assert tools[-1].input_schema["properties"]["status"]["enum"] == [
                    "pending", "processing", "on-hold", "completed", "cancelled", "failed"]
                return [tool.name for tool in tools]
