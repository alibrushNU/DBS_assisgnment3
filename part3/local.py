"""Run Swagger locally using the existing guarded Part 1 database configuration."""
import uvicorn

from part1.db import make_engine
from .app import create_app


def main():
    engine = make_engine()
    try:
        uvicorn.run(create_app(engine), host="127.0.0.1", port=8010)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
