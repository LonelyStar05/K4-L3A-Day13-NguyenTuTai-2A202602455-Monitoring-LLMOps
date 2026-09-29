from __future__ import annotations

"""Write 08-trace-metadata evidence with full metadata, model, usage and cost."""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from langfuse import Langfuse

EVIDENCE = REPO_ROOT / "submission" / "evidence"
c = Langfuse()
now = datetime.now(timezone.utc)
start = now - timedelta(hours=24)
end = now + timedelta(hours=1)

obs = c.api.observations.get_many(
    fields="core,basic,metadata,model,usage,cost",
    from_start_time=start,
    to_start_time=end,
    limit=100,
)

t_by_id: dict[str, list] = {}
for o in obs.data:
    tid = getattr(o, "trace_id", None)
    if tid:
        t_by_id.setdefault(tid, []).append(o)

# choose the rollback v1 production trace which was captured around 08:04:35
target = next(
    (t for t in t_by_id.items() if any(getattr(o, "is_root_observation", False) for o in t[1])),
    None,
)
if not target:
    raise SystemExit("no trace with root found")

tid, items = target
root = next(o for o in items if getattr(o, "is_root_observation", False))
gen = next((o for o in items if getattr(o, "type", None) == "GENERATION"), None)
ret = next((o for o in items if getattr(o, "type", None) == "RETRIEVER"), None)

lines = []
lines.append(f"trace_id={tid}")
lines.append(f"project=day13-k4-l3a-2A202602455")
lines.append(f"root: type={root.type} name={root.name} latency_s={root.latency} version={root.version}")
meta = {k: v for k, v in (root.metadata or {}).items() if not k.startswith(("scope.", "resourceAttributes."))}
lines.append(f"root metadata={json.dumps(meta, ensure_ascii=False)}")
if ret:
    lines.append(f"retriever: type={ret.type} name={ret.name} latency_s={ret.latency}")
if gen:
    lines.append(f"generation: type={gen.type} name={gen.name} latency_s={gen.latency}")
    lines.append(f"generation model={gen.model}")
    lines.append(f"generation usage_details={json.dumps(gen.usage_details, ensure_ascii=False) if gen.usage_details else None}")
    lines.append(f"generation cost_details={json.dumps(gen.cost_details, ensure_ascii=False) if getattr(gen, 'cost_details', None) else None}")
    lines.append(f"generation total_cost={getattr(gen, 'total_cost', None)}")

text = "\n".join(lines) + "\n"
(EVIDENCE / "08-trace-metadata.txt").write_text(text, encoding="utf-8")
print(text)
