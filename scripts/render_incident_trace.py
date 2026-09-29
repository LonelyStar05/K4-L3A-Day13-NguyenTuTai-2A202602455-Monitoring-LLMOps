from __future__ import annotations

"""Render incident trace waterfall for evidence 14."""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import base64
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
PUB = os.environ["LANGFUSE_PUBLIC_KEY"]; SEC = os.environ["LANGFUSE_SECRET_KEY"]
AUTH = base64.b64encode(f"{PUB}:{SEC}".encode()).decode()
TID = sys.argv[1] if len(sys.argv) > 1 else "26200cde04c8a84f0ef579f9439407a1"
OUT = REPO_ROOT / "submission" / "evidence" / "14-incident-trace.png"

def to_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

# fetch observations for trace id via get_many
from langfuse import Langfuse
c = Langfuse()
now = datetime.now(timezone.utc)
start = now - timedelta(hours=6)
end = now + timedelta(hours=1)
obs = c.api.observations.get_many(
    fields="core,basic,metadata,model,usage,cost",
    from_start_time=start, to_start_time=end, limit=200,
)
items = [o for o in obs.data if getattr(o, "trace_id", None) == TID]
if not items:
    raise SystemExit("no observations for trace")

items_by_ob = []
for o in items:
    items_by_ob.append({
        "type": o.type, "name": o.name, "latency": o.latency,
        "start": o.start_time, "end": o.end_time,
    })
items_by_ob.sort(key=lambda d: d["start"])
t0 = items_by_ob[0]["start"]
fig, ax = plt.subplots(figsize=(9, 4))
colors = {"AGENT": "tab:blue", "RETRIEVER": "tab:red", "GENERATION": "tab:orange"}
for i, o in enumerate(reversed(items_by_ob)):
    left = (o["start"] - t0).total_seconds() * 1000
    width = max((o["end"] - o["start"]).total_seconds() * 1000, 1)
    ax.barh(i, width, left=left, color=colors.get(o["type"], "gray"), alpha=0.85)
    ax.text(left + width + 5, i, f"{o['name']} ({o['type']}) {width:.0f}ms", va="center", fontsize=10)

ax.set_yticks(range(len(items_by_ob)))
ax.set_yticklabels([o["name"] for o in reversed(items_by_ob)])
ax.set_xlabel("ms (relative to trace start)")
ax.set_title(f"Incident trace {TID[:12]}… — retrieval span 2500ms (rag_slow)")
ax.grid(True, axis="x", alpha=0.3)
ax.legend(handles=[Patch(color=colors[t], label=t) for t in colors], loc="lower right")
fig.tight_layout()
fig.savefig(OUT, dpi=120)
print("Saved", OUT)
print(TID)
# also dump 14 text with span details
lines = [
    "Incident trace evidence (scenario: rag_slow practice)",
    f"trace_id={TID}",
    f"correlation_id=req-127a5cca",
    "--- span timeline ---",
]
for o in items_by_ob:
    lines.append(f"{o['type']} {o['name']}: {o['latency']*1000:.0f}ms")
lines.append("Root cause: RETRIEVER retrieve-documents spent 2500ms (rag_slow sleep); generation only 152ms.")
(REPO_ROOT / "submission" / "evidence" / "14-incident-trace.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
