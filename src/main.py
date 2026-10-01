"""Run the Streamable HTTP MCP server."""

import uvicorn

from config import Settings
from server import create_server


settings = Settings()
app = create_server(settings).http_app(stateless_http=True)


def main() -> None:
    """Load validated settings and start Uvicorn."""
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()
