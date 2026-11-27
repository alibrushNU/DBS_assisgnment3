"""Production entry point; the hosting provider supplies PORT and DATABASE_URL."""
import os

import uvicorn

from .initialize import main as initialize


def main():
    # Free Render services have no pre-deploy hook. This existing initializer
    # seeds a fresh schema once and preserves data on every later start.
    initialize()
    uvicorn.run("part3.app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))


if __name__ == "__main__":
    main()
