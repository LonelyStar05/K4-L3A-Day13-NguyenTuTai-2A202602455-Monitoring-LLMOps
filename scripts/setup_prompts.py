from __future__ import annotations

"""Manages the day13-chat prompt lifecycle in the personal Langfuse project.

Usage:
  python scripts/setup_prompts.py create
  python scripts/setup_prompts.py promote --version 2
  python scripts/setup_prompts.py rollback --version 1

Requires LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY and LANGFUSE_BASE_URL from .env.
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from langfuse import Langfuse

PROMPT_NAME = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")

V1_TEMPLATE = (
    "You are a concise assistant.\n"
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Answer in at most 3 sentences."
)

V2_TEMPLATE = (
    "You are a helpful assistant. Use ONLY the provided docs and cite the source when possible.\n"
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Keep the answer under 2 sentences and never expose PII."
)


def ensure_client() -> Langfuse:
    missing = [k for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY") if not os.getenv(k)]
    if missing:
        print("Missing environment variables: " + ", ".join(missing))
        print("Copy .env.example to .env and fill in your personal Langfuse keys.")
        raise SystemExit(1)
    return Langfuse()


def list_prompts(client: Langfuse) -> None:
    try:
        prompt = client.get_prompt(PROMPT_NAME)
        print(f"Current label 'production' -> version {prompt.version}")
    except Exception as exc:
        print(f"No production prompt found: {type(exc).__name__}")
    try:
        labels = client.api.prompts.get_labels(name=PROMPT_NAME)
        print(f"Labels: {labels}")
    except Exception as exc:
        print(f"Could not list labels: {type(exc).__name__}: {exc}")


def create_versions(client: Langfuse) -> None:
    v1 = client.create_prompt(
        name=PROMPT_NAME,
        prompt=V1_TEMPLATE,
        labels=["baseline", "production"],
        type="text",
        commit_message="v1 concise baseline",
    )
    print(f"Created prompt v1 (version {v1.version}) with labels baseline + production")
    v2 = client.create_prompt(
        name=PROMPT_NAME,
        prompt=V2_TEMPLATE,
        labels=["candidate"],
        type="text",
        commit_message="v2 two-sentence sourced candidate",
    )
    print(f"Created prompt v2 (version {v2.version}) with label candidate")


def set_production(client: Langfuse, version: int) -> None:
    client.update_prompt(name=PROMPT_NAME, version=version, new_labels=["production"])
    print(f"Set 'production' label to version {version}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create", "list", "promote", "rollback"])
    parser.add_argument("--version", type=int)
    args = parser.parse_args()

    client = ensure_client()
    if args.action == "create":
        create_versions(client)
    elif args.action == "list":
        list_prompts(client)
    elif args.action in ("promote", "rollback"):
        if not args.version:
            parser.error("--version is required for promote/rollback")
        set_production(client, args.version)

    client.flush()


if __name__ == "__main__":
    main()
