"""Runtime configuration for the HTTP listener."""

import os


def get_host() -> str:
    return os.getenv("MCP_HOST", "127.0.0.1")


def get_port() -> int:
    port = int(os.getenv("MCP_PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("MCP_PORT must be between 1 and 65535")
    return port
