"""MemU Service startup script."""

import uvicorn
from meow_agent.core.config import settings


def run():
    """Run the MemU Service."""
    uvicorn.run(
        "meow_agent.service:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    run()
