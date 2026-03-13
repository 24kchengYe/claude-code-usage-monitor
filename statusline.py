"""Claude Code statusline script.

Reads session JSON from stdin, merges with cached usage data,
outputs a single compact status line.

Configure in ~/.claude/settings.json:
{
  "statusLine": {
    "type": "command",
    "command": "python PATH_TO/statusline.py"
  }
}
"""

import json
import sys
import os

# Import usage_monitor from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usage_monitor


def main():
    # Read session JSON from stdin (provided by Claude Code)
    session = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            session = json.loads(raw)
    except Exception:
        pass

    # Extract model name
    model = ""
    if isinstance(session.get("model"), dict):
        model = session["model"].get("display_name", "")
    elif isinstance(session.get("model"), str):
        model = session["model"]

    # Shorten model name
    model_short = model
    for full, short in [
        ("Opus", "Opus"), ("Sonnet", "Sonnet"), ("Haiku", "Haiku"),
        ("claude-opus", "Opus"), ("claude-sonnet", "Sonnet"),
        ("claude-haiku", "Haiku"),
    ]:
        if full.lower() in model.lower():
            model_short = short
            break

    # Context window usage
    ctx = session.get("context_window", {})
    ctx_pct = ctx.get("used_percentage")

    # Session cost
    cost = session.get("cost", {})
    cost_usd = cost.get("total_cost_usd")

    # Fetch usage (cached, 60s TTL - won't hit API every time)
    data, _ = usage_monitor.fetch_usage(force=False)

    # Build status parts
    parts = []

    if model_short:
        parts.append(model_short)

    if ctx_pct is not None:
        parts.append(f"ctx:{int(ctx_pct)}%")

    if data:
        compact = usage_monitor.format_compact(data)
        if compact and compact != "usage: N/A":
            parts.append(compact)

    if cost_usd is not None:
        parts.append(f"${cost_usd:.2f}")

    print(" | ".join(parts) if parts else "")


if __name__ == "__main__":
    main()
