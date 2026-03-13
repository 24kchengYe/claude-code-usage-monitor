"""Claude Code statusline script.

Full-featured status line showing: model, git info, token usage,
reasoning effort, 5h/7d rate limits with reset times, extra usage.

All with ANSI RGB color coding matching oh-my-posh theme.

Configure in ~/.claude/settings.json:
{
  "statusLine": {
    "type": "command",
    "command": "python PATH_TO/statusline.py"
  }
}
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# Import usage_monitor from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usage_monitor

# ── ANSI RGB Colors (matching oh-my-posh theme) ──────────────────────

BLUE = "\033[38;2;0;153;255m"       # model name
CYAN = "\033[38;2;46;149;153m"      # directory
GREEN = "\033[38;2;0;160;0m"        # low usage / branch / additions
YELLOW = "\033[38;2;230;200;0m"     # moderate usage
ORANGE = "\033[38;2;255;176;85m"    # elevated usage
RED = "\033[38;2;255;85;85m"        # critical usage / deletions
WHITE = "\033[38;2;220;220;220m"    # labels
DIM = "\033[2m"                     # separators
RESET = "\033[0m"

SEP = f" {DIM}|{RESET} "


def color_pct(pct):
    """Return colored percentage string based on usage level."""
    if pct is None:
        return f"{DIM}-{RESET}"
    p = int(round(pct))
    if p >= 90:
        c = RED
    elif p >= 70:
        c = ORANGE
    elif p >= 50:
        c = YELLOW
    else:
        c = GREEN
    return f"{c}{p}%{RESET}"


def fmt_tokens(n):
    """Format token count: 1500000 -> '1.5m', 50000 -> '50k', 800 -> '800'."""
    if n is None:
        return "?"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}m"
    if n >= 1_000:
        return f"{n // 1_000}k"
    return str(n)


def fmt_reset_time(iso_str):
    """Convert ISO 8601 timestamp to local time string like '@14:30' or '@Mar 16, 14:30'."""
    if not iso_str:
        return ""
    try:
        clean = iso_str
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        target = datetime.fromisoformat(clean)
        now = datetime.now(timezone.utc)
        diff = (target - now).total_seconds()

        local_time = target.astimezone()

        if diff <= 0:
            return f" {DIM}(now){RESET}"

        # Same day: show just time
        now_local = now.astimezone()
        if local_time.date() == now_local.date():
            return f" {DIM}@{local_time.strftime('%H:%M')}{RESET}"

        # Within 7 days: show date + time
        if diff < 7 * 86400:
            return f" {DIM}@{local_time.strftime('%b %d, %H:%M')}{RESET}"

        return f" {DIM}@{local_time.strftime('%b %d')}{RESET}"
    except Exception:
        return ""


def get_git_info(cwd):
    """Get git branch and file changes for the working directory."""
    if not cwd:
        return None

    try:
        # Get branch name
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3, cwd=cwd
        )
        if branch.returncode != 0:
            return None
        branch_name = branch.stdout.strip()

        # Get file changes (added/deleted lines)
        diff = subprocess.run(
            ["git", "diff", "--numstat"],
            capture_output=True, text=True, timeout=3, cwd=cwd
        )
        added = 0
        deleted = 0
        if diff.returncode == 0 and diff.stdout.strip():
            for line in diff.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    try:
                        a = int(parts[0]) if parts[0] != "-" else 0
                        d = int(parts[1]) if parts[1] != "-" else 0
                        added += a
                        deleted += d
                    except ValueError:
                        pass

        # Get remote repo name (e.g. "24kchengYe/repo-name")
        remote_name = None
        try:
            remote = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=3, cwd=cwd
            )
            if remote.returncode == 0 and remote.stdout.strip():
                url = remote.stdout.strip()
                # Handle https://github.com/user/repo.git and git@github.com:user/repo.git
                if url.endswith(".git"):
                    url = url[:-4]
                if "github.com" in url:
                    if ":" in url.split("github.com")[-1]:
                        # git@github.com:user/repo
                        remote_name = url.split(":")[-1]
                    else:
                        # https://github.com/user/repo
                        parts = url.rstrip("/").split("/")
                        if len(parts) >= 2:
                            remote_name = parts[-2] + "/" + parts[-1]
        except Exception:
            pass

        # Get directory name
        dir_name = os.path.basename(cwd)

        return {
            "dir": dir_name,
            "branch": branch_name,
            "added": added,
            "deleted": deleted,
            "remote": remote_name,
        }
    except Exception:
        return None


def get_effort_level():
    """Get reasoning effort level from env var or settings.json."""
    # 1. Environment variable
    env = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL", "").strip().lower()
    if env in ("low", "medium", "high"):
        return env

    # 2. Settings file
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    settings_path = os.path.join(home, ".claude", "settings.json")
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        level = settings.get("effortLevel", "").strip().lower()
        if level in ("low", "medium", "high"):
            return level
    except Exception:
        pass

    return "medium"


def fmt_effort(level):
    """Format effort level with color."""
    colors = {
        "low": DIM,
        "medium": ORANGE,
        "high": GREEN,
    }
    short = {"low": "low", "medium": "med", "high": "high"}
    c = colors.get(level, DIM)
    label = short.get(level, level)
    return f"{c}{label}{RESET}"


def main():
    # Read session JSON from stdin (provided by Claude Code)
    session = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            session = json.loads(raw)
    except Exception:
        pass

    parts = []

    # ── 1. Model Name ──
    model = ""
    if isinstance(session.get("model"), dict):
        model = session["model"].get("display_name", "")
    elif isinstance(session.get("model"), str):
        model = session["model"]

    model_short = model
    for full, short in [
        ("Opus", "Opus"), ("Sonnet", "Sonnet"), ("Haiku", "Haiku"),
        ("claude-opus", "Opus"), ("claude-sonnet", "Sonnet"),
        ("claude-haiku", "Haiku"),
    ]:
        if full.lower() in model.lower():
            model_short = short
            break

    if model_short:
        parts.append(f"{BLUE}{model_short}{RESET}")

    # ── 2. Git Info (dir@branch +added -deleted) ──
    cwd = session.get("cwd", "")
    git_info = get_git_info(cwd)
    if git_info:
        # Show remote repo name if available, plus local dir
        if git_info.get("remote"):
            name_part = f"{CYAN}{git_info['remote']}{RESET}"
        else:
            name_part = f"{CYAN}{git_info['dir']}{RESET}"
        git_part = f"{name_part}{DIM}@{RESET}{GREEN}{git_info['branch']}{RESET}"
        if git_info["added"] > 0 or git_info["deleted"] > 0:
            changes = []
            if git_info["added"] > 0:
                changes.append(f"{GREEN}+{git_info['added']}{RESET}")
            if git_info["deleted"] > 0:
                changes.append(f"{RED}-{git_info['deleted']}{RESET}")
            git_part += f" {DIM}({RESET}{' '.join(changes)}{DIM}){RESET}"
        parts.append(git_part)
    elif cwd:
        dir_name = os.path.basename(cwd)
        if dir_name:
            parts.append(f"{CYAN}{dir_name}{RESET}")

    # ── 3. Token Usage (50k/200k (25%)) ──
    ctx = session.get("context_window", {})
    usage = ctx.get("current_usage", {})
    ctx_size = ctx.get("context_window_size")

    input_tokens = usage.get("input_tokens", 0) or 0
    cache_create = usage.get("cache_creation_input_tokens", 0) or 0
    cache_read = usage.get("cache_read_input_tokens", 0) or 0
    current_tokens = input_tokens + cache_create + cache_read

    if ctx_size and ctx_size > 0:
        token_pct = (current_tokens * 100) / ctx_size
        parts.append(
            f"{ORANGE}{fmt_tokens(current_tokens)}{RESET}"
            f"{DIM}/{RESET}"
            f"{fmt_tokens(ctx_size)}"
            f" {DIM}({RESET}{color_pct(token_pct)}{DIM}){RESET}"
        )
    else:
        # Fallback to simple percentage if available
        ctx_pct = ctx.get("used_percentage")
        if ctx_pct is not None:
            parts.append(f"ctx:{color_pct(ctx_pct)}")

    # ── 4. Reasoning Effort ──
    effort = get_effort_level()
    parts.append(f"{WHITE}effort:{RESET} {fmt_effort(effort)}")

    # ── 5. Rate Limits (5h/7d) with reset times ──
    data, _ = usage_monitor.fetch_usage(force=False)
    if data:
        five_h = data.get("five_hour", {})
        seven_d = data.get("seven_day", {})

        five_pct = five_h.get("utilization")
        seven_pct = seven_d.get("utilization")

        if five_pct is not None:
            reset = fmt_reset_time(five_h.get("resets_at"))
            parts.append(f"{WHITE}5h{RESET} {color_pct(five_pct)}{reset}")

        if seven_pct is not None:
            reset = fmt_reset_time(seven_d.get("resets_at"))
            parts.append(f"{WHITE}7d{RESET} {color_pct(seven_pct)}{reset}")

        # ── 6. Extra Usage ──
        extra = data.get("extra_usage", {})
        if extra and extra.get("is_enabled"):
            used = extra.get("used_credits")
            limit = extra.get("monthly_limit")
            if used is not None and limit is not None:
                parts.append(
                    f"{WHITE}extra{RESET} "
                    f"{GREEN}${used / 100:.2f}{RESET}"
                    f"{DIM}/{RESET}"
                    f"${limit / 100:.2f}"
                )
            else:
                parts.append(f"{WHITE}extra{RESET} {GREEN}enabled{RESET}")
    else:
        parts.append(f"{WHITE}5h{RESET} {DIM}-{RESET}")
        parts.append(f"{WHITE}7d{RESET} {DIM}-{RESET}")

    # ── 7. Session Cost ──
    cost = session.get("cost", {})
    cost_usd = cost.get("total_cost_usd")
    if cost_usd is not None:
        parts.append(f"{DIM}${cost_usd:.2f}{RESET}")

    # Output
    print(SEP.join(parts) if parts else "")


if __name__ == "__main__":
    main()
