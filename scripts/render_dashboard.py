from __future__ import annotations

"""Render the six-panel Day 13 dashboard from data/logs.jsonl.

This is a local helper to generate runtime dashboard evidence. The scoring
contract remains config/dashboard.yaml (validated by validate_dashboard.py).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

def load_records(path: Path) -> list[dict]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def main() -> int:
    configure_utf8_stdio()
    log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "data" / "logs.jsonl"
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO_ROOT / "submission" / "evidence" / "11-dashboard-overview.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    records = load_records(log_path)
    if not records:
        print("No records found in", log_path)
        return 1

    responses = [r for r in records if r.get("event") == "response_sent"]
    received = [r for r in records if r.get("event") == "request_received"]
    failed = [r for r in records if r.get("event") == "request_failed"]

    latencies = [r["latency_ms"] for r in responses if "latency_ms" in r]
    ttfts = [r["ttft_ms"] for r in responses if "ttft_ms" in r]
    costs = [r["cost_usd"] for r in responses if "cost_usd" in r]
    tokens_in = [r["tokens_in"] for r in responses if "tokens_in" in r]
    tokens_out = [r["tokens_out"] for r in responses if "tokens_out" in r]
    quality = [r["quality_score"] for r in responses if "quality_score" in r]
    success = [r for r in responses if r.get("tool_success") is True]

    fig, axes = plt.subplots(3, 2, figsize=(20, 14))
    fig.suptitle("K4-L3A Day 13 Monitoring & LLMOps — Dashboard (60 min)", fontsize=18)

    x_series = list(range(len(responses)))

    # Panel 1: latency
    ax = axes[0][0]
    p50, p95, p99, ttft_p95 = pct(latencies, 50), pct(latencies, 95), pct(latencies, 99), pct(ttfts, 95)
    ax.plot(x_series, latencies, label="latency_ms", alpha=0.5)
    ax.axhline(p95, color="red", linestyle="--", label=f"P95={p95:.0f}ms (threshold 3000ms)")
    ax.set_title("Latency percentiles and TTFT (ms)")
    ax.set_xlabel("request index")
    ax.set_ylabel("ms")
    ax.legend()
    ax.text(0.01, 0.98, f"P50={p50:.0f}ms  P95={p95:.0f}ms  P99={p99:.0f}ms  TTFT_P95={ttft_p95:.0f}ms", transform=ax.transAxes, verticalalignment="top", fontsize=9)

    # Panel 2: traffic
    ax = axes[0][1]
    ax.bar(list(range(len(received))), [1] * len(received), label=f"requests={len(received)}")
    ax.set_title("Request traffic (requests_per_minute)")
    ax.set_ylabel("requests")
    ax.legend()

    # Panel 3: errors
    ax = axes[1][0]
    err_rate = (len(failed) / len(received) * 100) if received else 0
    succ_rate = (len(success) / len(responses) * 100) if responses else 0
    ax.bar(["error_rate_pct"], [err_rate], color="red")
    ax.bar(["retrieval_success_pct"], [succ_rate], color="green")
    ax.axhline(2, color="red", linestyle="--", label="error threshold 2%")
    ax.set_title("Error rate and retrieval success (percent)")
    ax.set_ylabel("percent")
    ax.legend()

    # Panel 4: cost
    ax = axes[1][1]
    ax.plot(x_series, costs, label="cost_usd")
    ax.set_title("Cost over time (usd)")
    ax.set_ylabel("usd")
    ax.text(0.01, 0.98, f"total={sum(costs):.4f} usd", transform=ax.transAxes, verticalalignment="top", fontsize=9)
    ax.legend()

    # Panel 5: tokens
    ax = axes[2][0]
    ax.bar(["input_tokens"], [sum(tokens_in)], color="blue")
    ax.bar(["output_tokens"], [sum(tokens_out)], color="orange")
    ax.set_title("Input and output tokens (tokens)")
    ax.set_ylabel("tokens")
    ax.legend()

    # Panel 6: quality
    ax = axes[2][1]
    mean_q = sum(quality) / len(quality) if quality else 0
    ax.plot(x_series, quality, label="quality_score")
    ax.axhline(0.75, color="green", linestyle="--", label="threshold 0.75")
    ax.set_title("Quality proxy (score_0_to_1)")
    ax.set_ylabel("score")
    ax.text(0.01, 0.98, f"mean={mean_q:.2f}", transform=ax.transAxes, verticalalignment="top", fontsize=9)
    ax.legend()

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_path, dpi=120)
    print("Saved dashboard to", out_path)
    print(f"requests={len(received)} responses={len(responses)} failed={len(failed)}")
    print(f"latency P50/P95/P99={p50:.0f}/{p95:.0f}/{p99:.0f} TTFT_P95={ttft_p95:.0f}")
    print(f"error_rate_pct={err_rate:.2f} retrieval_success_pct={succ_rate:.2f} quality_mean={mean_q:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
