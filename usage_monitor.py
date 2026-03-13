"""Claude Code usage monitor - core library.

Reads OAuth credentials from ~/.claude/.credentials.json,
calls the Anthropic usage API (proxy-aware via Python urllib),
caches results, and provides compact/detailed formatting.

Works on Windows, macOS, and Linux.
"""

import json
import os
import sys
import time
import tempfile
import urllib.request
import urllib.error

USAGE_API = "https://api.anthropic.com/api/oauth/usage"
ANTHROPIC_BETA = "oauth-2025-04-20"
CACHE_TTL = 60  # seconds
USER_AGENT = "claude-code-usage-monitor/1.0"


def _home_dir():
    """Get user home directory, cross-platform."""
    return os.environ.get("USERPROFILE") or os.path.expanduser("~")


def _credentials_path():
    return os.path.join(_home_dir(), ".claude", ".credentials.json")


def _cache_path():
    return os.path.join(tempfile.gettempdir(), "claude-usage-cache.json")


def _detect_proxy():
    """Detect proxy from env vars, then Windows registry fallback."""
    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy",
                "ALL_PROXY", "all_proxy"):
        val = os.environ.get(var)
        if val:
            return val

    # Windows registry fallback
    if sys.platform == "win32" or os.name == "nt":
        try:
            import subprocess
            result = subprocess.run(
                ["reg", "query",
                 r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                 "/v", "ProxyEnable"],
                capture_output=True, text=True, timeout=3
            )
            if "0x1" in result.stdout:
                result2 = subprocess.run(
                    ["reg", "query",
                     r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                     "/v", "ProxyServer"],
                    capture_output=True, text=True, timeout=3
                )
                for line in result2.stdout.splitlines():
                    line = line.strip()
                    if "ProxyServer" in line:
                        parts = line.split()
                        proxy = parts[-1]
                        if not proxy.startswith("http"):
                            proxy = "http://" + proxy
                        return proxy
        except Exception:
            pass
    return None


def _install_proxy():
    """Install proxy handler for urllib if detected."""
    proxy = _detect_proxy()
    if proxy:
        handler = urllib.request.ProxyHandler({
            "http": proxy,
            "https": proxy,
        })
        opener = urllib.request.build_opener(handler)
        urllib.request.install_opener(opener)


def get_oauth_token():
    """Read OAuth access token and plan from credentials file."""
    try:
        with open(_credentials_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        oauth = data.get("claudeAiOauth", {})
        token = oauth.get("accessToken")
        plan = oauth.get("subscriptionType", "unknown")
        return token, plan
    except Exception:
        return None, None


def _read_cache():
    """Read cached usage data if fresh enough."""
    path = _cache_path()
    try:
        mtime = os.path.getmtime(path)
        if time.time() - mtime > CACHE_TTL:
            return None, path
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), path
    except Exception:
        return None, path


def _write_cache(data, path):
    try:
        os.makedirs(os.path.dirname(path) or tempfile.gettempdir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def fetch_usage(force=False):
    """Fetch usage data from API or cache.

    Returns:
        tuple: (data_dict, error_str) - data may be cached on error
    """
    cached, cache_path = _read_cache()
    if cached and not force:
        return cached, None

    token, plan = get_oauth_token()
    if not token:
        return cached, "not logged in - run Claude Code and /login first"

    _install_proxy()

    req = urllib.request.Request(USAGE_API, method="GET", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "anthropic-beta": ANTHROPIC_BETA,
        "User-Agent": USER_AGENT,
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        data["_plan"] = plan
        data["_fetched_at"] = time.time()
        _write_cache(data, cache_path)
        return data, None
    except urllib.error.HTTPError as e:
        return cached, f"HTTP {e.code}"
    except Exception as e:
        return cached, str(e)


def _pct(utilization):
    if utilization is None:
        return None
    try:
        return int(round(float(utilization)))
    except (TypeError, ValueError):
        return None


def _time_until(iso_str):
    """Return human-readable countdown from now to ISO timestamp."""
    if not iso_str:
        return None
    try:
        from datetime import datetime, timezone
        clean = iso_str
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        target = datetime.fromisoformat(clean)
        now = datetime.now(timezone.utc)
        diff = (target - now).total_seconds()

        if diff <= 0:
            return "now"
        if diff < 3600:
            return f"{int(diff / 60)}m"
        if diff < 172800:
            return f"{int(diff / 3600)}h{int((diff % 3600) / 60)}m"
        return f"{int(diff / 86400)}d{int((diff % 86400) / 3600)}h"
    except Exception:
        return None


def _bar(pct, width=10):
    """Create a simple ASCII progress bar."""
    if pct is None:
        return "[" + "?" * width + "]"
    filled = int(round(pct / 100 * width))
    filled = max(0, min(width, filled))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _color_pct(pct):
    """Return ANSI-colored percentage string."""
    if pct is None:
        return "N/A"
    if pct >= 90:
        return f"\033[31m{pct}%\033[0m"  # red
    if pct >= 70:
        return f"\033[33m{pct}%\033[0m"  # yellow
    return f"\033[32m{pct}%\033[0m"  # green


def format_compact(data):
    """One-line compact output for statusline."""
    if not data:
        return "usage: N/A"

    five = _pct(data.get("five_hour", {}).get("utilization"))
    seven = _pct(data.get("seven_day", {}).get("utilization"))

    parts = []
    if five is not None:
        parts.append(f"5h:{five}%")
    if seven is not None:
        parts.append(f"7d:{seven}%")

    return " ".join(parts) if parts else "usage: N/A"


def format_detailed(data):
    """Multi-line detailed output with progress bars and colors."""
    if not data:
        return "No usage data available."

    plan = data.get("_plan", "unknown")
    plan_labels = {
        "pro": "Pro ($20/month)",
        "max_5x": "Max 5x ($100/month)",
        "max": "Max 20x ($200/month)",
    }
    plan_display = plan_labels.get(plan, plan)

    five_h = data.get("five_hour", {})
    seven_d = data.get("seven_day", {})
    sonnet = data.get("seven_day_sonnet", {})
    opus = data.get("seven_day_opus", {})
    extra = data.get("extra_usage", {})

    five_pct = _pct(five_h.get("utilization"))
    seven_pct = _pct(seven_d.get("utilization"))
    sonnet_pct = _pct(sonnet.get("utilization")) if sonnet else None
    opus_pct = _pct(opus.get("utilization")) if opus else None

    five_reset = _time_until(five_h.get("resets_at"))
    seven_reset = _time_until(seven_d.get("resets_at"))

    lines = []
    lines.append("=" * 42)
    lines.append("  Claude Code Usage Report")
    lines.append("=" * 42)
    lines.append(f"  Plan: {plan_display}")
    lines.append("")

    lines.append("  5-Hour Window (short-term)")
    lines.append(f"    Usage:  {_bar(five_pct)} {_color_pct(five_pct)}")
    if five_reset:
        lines.append(f"    Resets: in {five_reset}")
    lines.append("")

    lines.append("  7-Day Window (long-term)")
    lines.append(f"    Usage:  {_bar(seven_pct)} {_color_pct(seven_pct)}")
    if seven_reset:
        lines.append(f"    Resets: in {seven_reset}")
    lines.append("")

    if sonnet_pct is not None:
        lines.append(f"  Sonnet 7-Day: {_bar(sonnet_pct)} {_color_pct(sonnet_pct)}")
    if opus_pct is not None:
        lines.append(f"  Opus 7-Day:   {_bar(opus_pct)} {_color_pct(opus_pct)}")
    if sonnet_pct is not None or opus_pct is not None:
        lines.append("")

    if extra and extra.get("is_enabled"):
        used = extra.get("used_credits")
        limit = extra.get("monthly_limit")
        if used is not None and limit is not None:
            lines.append(f"  Extra Usage: ${used/100:.2f} / ${limit/100:.2f}")
        else:
            lines.append("  Extra Usage: Enabled")
    else:
        lines.append("  Extra Usage: Disabled")

    lines.append("=" * 42)
    return "\n".join(lines)


def format_json(data):
    """JSON output for programmatic use."""
    if not data:
        return "{}"
    # Strip internal fields
    out = {k: v for k, v in data.items() if not k.startswith("_")}
    out["plan"] = data.get("_plan", "unknown")
    return json.dumps(out, indent=2)


if __name__ == "__main__":
    # Force UTF-8 output on Windows
    if sys.platform == "win32" or os.name == "nt":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    force = "--force" in sys.argv or "-f" in sys.argv
    detailed = "--detailed" in sys.argv or "-d" in sys.argv
    as_json = "--json" in sys.argv

    data, err = fetch_usage(force=force)
    if err and not data:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    if as_json:
        print(format_json(data))
    elif detailed:
        print(format_detailed(data))
    else:
        print(format_compact(data))
