"""Detailed usage report script for the usage-monitor skill."""

import sys
import os

# Add ~/.claude to path to import usage_monitor
claude_dir = os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"), ".claude")
sys.path.insert(0, claude_dir)

import usage_monitor

def main():
    force = "--force" in sys.argv or "-f" in sys.argv
    data, err = usage_monitor.fetch_usage(force=force)

    if err and not data:
        print(f"Error fetching usage: {err}")
        sys.exit(1)

    if err:
        print(f"(Using cached data, API error: {err})\n")

    print(usage_monitor.format_detailed(data))


if __name__ == "__main__":
    main()
