from __future__ import annotations

"""Send one chat request in-process to generate a trace for a given prompt label."""

import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

label = sys.argv[1] if len(sys.argv) > 1 else "production"
os.environ["LANGFUSE_PROMPT_LABEL"] = label

from app.main import app
import httpx

async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/chat",
            json={
                "user_id": "prompt-check",
                "session_id": "prompt-lifecycle",
                "feature": "qa",
                "message": "Explain how observability ties metrics logs and traces together",
            },
        )
        body = r.json()
        print(r.status_code, body.get("correlation_id"), "label=", label)
        # flush Langfuse before exit
        try:
            from langfuse import get_client
            get_client().flush()
        except Exception:
            pass

asyncio.run(main())
