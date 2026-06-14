import subprocess
import json
import os
import sys
import logging

logger = logging.getLogger(__name__)

class WorkspaceMCPClient:
    """
    A lightweight standard-I/O based JSON-RPC client to communicate with 
    the project-provided custom Google Workspace MCP Server.
    """
    def __init__(self):
        self.process = None
        self.msg_id = 0
        
    def connect(self):
        """Spawns the MCP server Node process and performs the initialization handshake."""
        server_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "mcp-server", 
            "index.js"
        )
        
        logger.info(f"Spawning Workspace MCP server process at: {server_path}")
        
        # Spawn the node server process
        self.process = subprocess.Popen(
            ["node", server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=1 # Line buffered
        )
        
        # 1. Send initialize request
        init_id = self._next_id()
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "groww-pipeline-client",
                    "version": "1.0.0"
                }
            },
            "id": init_id
        }
        
        self._write_line(init_request)
        init_response = self._read_line()
        
        if not init_response or init_response.get("id") != init_id:
            raise RuntimeError(f"Failed to initialize MCP Server. Response: {init_response}")
            
        logger.info("MCP Server initialized handshake step 1 completed.")
        
        # 2. Send initialized notification (no ID, no response expected)
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        self._write_line(initialized_notification)
        logger.info("MCP Client connection fully established.")

    def call_tool(self, tool_name, arguments):
        """Calls an MCP tool and returns the parsed result."""
        if not self.process:
            raise RuntimeError("MCP Client is not connected. Call connect() first.")
            
        call_id = self._next_id()
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": call_id
        }
        
        logger.info(f"Calling MCP Tool: {tool_name}")
        self._write_line(request)
        response = self._read_line()
        
        if not response:
            raise RuntimeError(f"Received empty response from MCP server for tool: {tool_name}")
            
        if "error" in response:
            raise RuntimeError(f"MCP Server JSON-RPC Error: {response['error']}")
            
        result = response.get("result", {})
        if result.get("isError"):
            error_content = result.get("content", [{}])[0].get("text", "Unknown error")
            raise RuntimeError(f"MCP Tool Execution Error: {error_content}")
            
        # Parse the inner JSON text content
        content_items = result.get("content", [])
        if not content_items:
            return {}
            
        text_content = content_items[0].get("text", "{}")
        try:
            return json.loads(text_content)
        except json.JSONDecodeError:
            return {"raw_text": text_content}

    def close(self):
        """Gracefully closes the MCP server process."""
        if self.process:
            logger.info("Closing MCP server subprocess...")
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def _next_id(self):
        self.msg_id += 1
        return self.msg_id

    def _write_line(self, data):
        line = json.dumps(data) + "\n"
        self.process.stdin.write(line)
        self.process.stdin.flush()

    def _read_line(self):
        # Read stdout line by line
        line = self.process.stdout.readline()
        if not line:
            # If stdout closed, check stderr for errors
            if self.process.stderr:
                stderr_content = self.process.stderr.read()
                if stderr_content:
                    logger.error(f"MCP Server Stderr Log: {stderr_content}")
            return None
            
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            logger.warning(f"MCP client received non-JSON stdout: {line.strip()}")
            return self._read_line()
