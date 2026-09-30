"""Run the API with Railway-aware host and port settings."""

import uvicorn

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.effective_port,
    )


if __name__ == "__main__":
    main()
