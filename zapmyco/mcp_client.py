import asyncio
from typing import Optional
from contextlib import AsyncExitStack
import importlib.util
import sys
import os
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp import FastMCP
from zapmyco.mcp_servers.home_assistant import MCPHomeAssistant

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

        print(available_tools)


async def load_mcp_server(server_path):
    """在当前进程中加载 MCP 服务器模块并返回 mcp 实例"""
    # 加载模块
    spec = importlib.util.spec_from_file_location("mcp_server", server_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["mcp_server"] = module
    spec.loader.exec_module(module)

    # 返回 mcp 实例
    return module.mcp


async def main():
    res = await MCPHomeAssistant.list_tools()
    tools_dict = [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema,
        }
        for tool in res
    ]
    print(tools_dict)
    # print(tools.to_dict())
    # print(json.dumps())
    # # 加载 MCP 服务器
    # mcp_server_path = (
    #     "/Users/nemo/github/zapmyco/zapmyco/zapmyco/mcp_servers/home_assistant.py"
    # )
    # mcp_server = await load_mcp_server(mcp_server_path)
    # print(f"\nLoaded MCP server with tools: {[tool.name for tool in mcp_server.tools]}")

    # # 创建客户端并连接
    # client = MCPClient()
    # await client.connect_to_server(mcp_server_path)
    # await client.process_query("test")


if __name__ == "__main__":
    import sys

    asyncio.run(main())
