from __future__ import annotations

"""Render one Langfuse trace waterfall (root -> retriever -> generation) from real observations."""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

BASE = os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
PUB = os.environ["LANGFUSE_PUBLIC_KEY"]
SEC = os.environ["LANGFUSE_SECRET_KEY"]
AUTH = __import__("base64").b64encode(f"{PUB}:{SEC}".encode()).decode()
OUT = REPO_ROOT / "submission" / "evidence" / "07-trace-waterfall.png"


def fetch_observations() -> list[dict]:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=24)).isoformat()
    end = (now + timedelta(hours=1)).isoformat()
    r = httpx.get(
        f"{BASE}/api/public/v2/observations",
        headers={"Authorization": f"Basic {AUTH}"},
        params={"fromStartTime": start, "toStartTime": end, "limit": 50},
    )
    r.raise_for_status()
    return r.json()["data"]


def to_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> int:
    obs = fetch_observations()
    by_trace: dict[str, list[dict]] = {}
    for o in obs:
        if o.get("traceId"):
            by_trace.setdefault(o["traceId"], []).append(o)

    # Pick a trace with at least 3 observations (root, retrieval, generation)
    target = None
    for tid, items in by_trace.items():
        if len(items) >= 3:
            target = (tid, items)
            break
    if not target:
        print("No trace with 3 observations found")
        return 1

    tid, items = target
    items = sorted(items, key=lambda o: to_dt(o["startTime"]))

    # Use root start as relative zero
    t0 = to_dt(items[0]["startTime"])
    fig, ax = plt.subplots(figsize=(9, 4))
    colors = {"AGENT": "tab:blue", "RETRIEVER": "tab:green", "GENERATION": "tab:orange"}
    for i, o in enumerate(reversed(items)):
        start = to_dt(o["startTime"])
        end = to_dt(o["endTime"])
        left = (start - t0).total_seconds() * 1000
        width = max((end - start).total_seconds() * 1000, 1)
        ax.barh(i, width, left=left, color=colors.get(o["type"], "gray"), alpha=0.85)
        ax.text(left + width + 2, i, f"{o['name']} ({o['type']}) {width:.0f}ms", va="center", fontsize=9)

    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([o["name"] for o in reversed(items)])
    ax.set_xlabel("ms (relative to trace start)")
    ax.set_title(f"Trace waterfall — {tid[:12]}… (day13-k4-l3a-2A202602455)")
    ax.grid(True, axis="x", alpha=0.3)
    legend = [Patch(color=c, label=t) for t, c in colors.items()]
    ax.legend(handles=legend, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT, dpi=120)
    print("Saved", OUT, "trace_id", tid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
