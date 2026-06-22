import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class MCPServerInstance:
    def __init__(self, name: str, command: str, args: list[str], env: dict[str, str]):
        self.name = name
        self.command = command
        self.args = args
        self.env = env
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._tools: list[dict] = []
        self._lock = asyncio.Lock()

    async def start(self):
        if self.command == "docker":
            full_args = list(self.args)
            env_flags = []
            for key, value in self.env.items():
                if value:
                    env_flags.extend(["-e", f"{key}={value}"])
            # Insert env flags before the last argument (the image)
            image_idx = len(full_args) - 1
            full_args = full_args[:image_idx] + env_flags + full_args[image_idx:]

            self._process = await asyncio.create_subprocess_exec(
                self.command, *full_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=10 * 1024 * 1024,  # 10MB buffer for large tool lists
            )
        else:
            import os
            process_env = {**os.environ, **self.env}
            self._process = await asyncio.create_subprocess_exec(
                self.command, *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                limit=10 * 1024 * 1024,
            )

        await self._initialize()
        logger.info("MCP server '%s' started with %d tools", self.name, len(self._tools))

    async def _initialize(self):
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "agentic-incident-intelligence", "version": "0.1.0"},
        })
        await self._send_notification("notifications/initialized", {})
        tools_response = await self._send_request("tools/list", {})
        self._tools = tools_response.get("tools", [])

    async def _send_request(self, method: str, params: dict) -> dict:
        async with self._lock:
            self._request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params,
            }
            await self._write(request)
            return await self._read_response(self._request_id)

    async def _send_notification(self, method: str, params: dict):
        async with self._lock:
            notification = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
            await self._write(notification)

    async def _write(self, data: dict):
        if not self._process or not self._process.stdin:
            raise RuntimeError(f"MCP process '{self.name}' not running")
        line = json.dumps(data) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

    async def _read_response(self, expected_id: int) -> dict:
        if not self._process or not self._process.stdout:
            raise RuntimeError(f"MCP process '{self.name}' not running")

        while True:
            # MCP tool lists can be very large, so use a 10MB readline limit
            line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=30,
            )
            if not line:
                stderr = ""
                if self._process.stderr:
                    stderr = (await self._process.stderr.read()).decode()
                raise RuntimeError(f"MCP process '{self.name}' closed. stderr: {stderr[:500]}")

            line_str = line.decode().strip()
            if not line_str:
                continue

            try:
                response = json.loads(line_str)
            except json.JSONDecodeError:
                continue

            if response.get("id") == expected_id:
                if "error" in response:
                    raise RuntimeError(f"MCP error from '{self.name}': {response['error']}")
                return response.get("result", {})

    def get_tools(self) -> list[dict]:
        return self._tools

    def get_tool_definitions_for_claude(self) -> list[dict]:
        tools = []
        for tool in self._tools:
            tools.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}}),
            })
        return tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        content = response.get("content", [])
        text_parts = []
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block["text"])
        return "\n".join(text_parts) if text_parts else json.dumps(content)

    async def stop(self):
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
            self._process = None

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None


class MCPManager:
    def __init__(self):
        self._servers: dict[str, MCPServerInstance] = {}

    async def register_server(self, name: str, command: str, args: list[str], env: dict[str, str]) -> list[dict]:
        if name in self._servers and self._servers[name].is_running:
            await self._servers[name].stop()

        server = MCPServerInstance(name=name, command=command, args=args, env=env)
        await server.start()
        self._servers[name] = server
        return server.get_tool_definitions_for_claude()

    async def unregister_server(self, name: str):
        if name in self._servers:
            await self._servers[name].stop()
            del self._servers[name]

    def get_all_tools(self) -> list[dict]:
        tools = []
        for server in self._servers.values():
            if server.is_running:
                tools.extend(server.get_tool_definitions_for_claude())
        return tools

    def get_all_tool_names(self) -> list[str]:
        return [t["name"] for t in self.get_all_tools()]

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        for server in self._servers.values():
            if server.is_running:
                server_tool_names = [t["name"] for t in server.get_tools()]
                if tool_name in server_tool_names:
                    return await server.call_tool(tool_name, arguments)
        raise RuntimeError(f"No MCP server has tool: {tool_name}")

    async def stop_all(self):
        for server in list(self._servers.values()):
            await server.stop()
        self._servers.clear()

    @property
    def running_servers(self) -> list[str]:
        return [name for name, s in self._servers.items() if s.is_running]


mcp_manager = MCPManager()
