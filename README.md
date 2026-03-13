![Visitors](https://visitor-badge.laobi.icu/badge?page_id=24kchengYe.claude-code-usage-monitor)

# claude-code-usage-monitor

> **Real-time Claude Code subscription usage monitoring — as a skill, statusline widget, or standalone CLI.**

Stop guessing how much quota you've burned. See your 5-hour session limit, 7-day rolling usage, per-model breakdown, and reset countdowns — all without leaving Claude Code.

## Why This Exists

Claude Code's Pro/Max subscriptions have **two hidden rate-limit windows** that throttle you when exceeded:

| Window | What happens at 100% |
|--------|---------------------|
| **5-hour** | Temporary slowdown until the window slides |
| **7-day** | Week-long rate limiting |

This tool makes those invisible limits visible — in your statusline, via a skill command, or as a standalone script.

## Features

- **Statusline widget** — Always-visible usage in Claude Code's bottom bar: `Opus | ctx:25% | 5h:6% 7d:17% | $0.42`
- **Skill integration** — Say "查看用量" or "check usage" to get a detailed report with progress bars and reset countdowns
- **Standalone CLI** — Run from any terminal: `python usage_monitor.py --detailed`
- **Proxy-aware** — Uses Python `urllib` which natively respects `HTTPS_PROXY`, unlike Node.js `fetch` (looking at you, quotapulse)
- **Zero dependencies** — Pure Python standard library, no `pip install` needed
- **60-second smart cache** — Won't hammer the API on every statusline refresh
- **Cross-platform** — Windows, macOS, Linux

## Install

### As a Claude Code Skill (recommended)

```bash
# One-line install
git clone https://github.com/24kchengYe/claude-code-usage-monitor.git ~/.claude/skills/usage-monitor
```

Windows:

```bash
git clone https://github.com/24kchengYe/claude-code-usage-monitor.git %USERPROFILE%\.claude\skills\usage-monitor
```

Then add the statusline to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python ~/.claude/skills/usage-monitor/statusline.py"
  }
}
```

Windows users use forward slashes in the command path:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python C:/Users/YOUR_NAME/.claude/skills/usage-monitor/statusline.py"
  }
}
```

### Standalone (no skill)

Just download `usage_monitor.py` and run it:

```bash
curl -o usage_monitor.py https://raw.githubusercontent.com/24kchengYe/claude-code-usage-monitor/master/usage_monitor.py
python usage_monitor.py --detailed
```

## Usage

### In Claude Code (Skill)

Just say any of these:

```
查看用量
check usage
还剩多少额度
/usage
show my quota
```

Claude will run the monitor and show you a detailed report.

### Statusline

Once configured, the bottom bar automatically shows:

```
Opus | ctx:25% | 5h:6% 7d:17% | $0.42
       ^         ^      ^        ^
       |         |      |        session cost
       |         |      7-day window usage
       |         5-hour window usage
       context window used
```

### CLI

```bash
# Compact (for scripts/statusline)
python usage_monitor.py
# Output: 5h:6% 7d:17%

# Detailed report with progress bars
python usage_monitor.py --detailed
# Output:
# ==========================================
#   Claude Code Usage Report
# ==========================================
#   Plan: Max 20x ($200/month)
#
#   5-Hour Window (short-term)
#     Usage:  [#---------] 6%
#     Resets: in 3h44m
#
#   7-Day Window (long-term)
#     Usage:  [##--------] 17%
#     Resets: in 3d12h
#
#   Extra Usage: Disabled
# ==========================================

# JSON output
python usage_monitor.py --json

# Force refresh (bypass 60s cache)
python usage_monitor.py --detailed --force
```

## How It Works

1. Reads your OAuth token from `~/.claude/.credentials.json` (created when you log in to Claude Code)
2. Calls the Anthropic usage API (`api.anthropic.com/api/oauth/usage`)
3. Caches the response for 60 seconds to avoid rate limiting
4. Formats the output as compact text, detailed report, or JSON

### Proxy Support

Unlike tools that use Node.js `fetch` (which ignores `HTTPS_PROXY`), this tool uses Python's `urllib` which **automatically respects system proxy settings**:

- `HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY` environment variables
- Windows system proxy (registry fallback for Clash/V2Ray/SSR users)

No manual proxy configuration needed.

## Supported Plans

| Plan | Monthly Cost | Tested |
|------|-------------|--------|
| Pro | $20 | Planned |
| Max 5x | $100 | Planned |
| Max 20x | $200 | Yes |

## API Response Fields

| Field | Description |
|-------|-------------|
| `five_hour.utilization` | 5-hour rolling window usage (0-100) |
| `seven_day.utilization` | 7-day rolling window usage (0-100) |
| `seven_day_sonnet.utilization` | Sonnet-specific 7-day usage |
| `seven_day_opus.utilization` | Opus-specific 7-day usage |
| `extra_usage.used_credits` | Extra usage charges in cents |
| `*.resets_at` | ISO 8601 timestamp for window reset |

## File Structure

```
usage-monitor/
├── SKILL.md            ← Claude Code skill definition
├── README.md
├── usage_monitor.py    ← Core library + CLI entry point
├── statusline.py       ← Statusline script (reads stdin JSON)
└── scripts/
    └── show_usage.py   ← Detailed report script
```

## Requirements

- Python 3.7+ (no additional packages needed)
- Claude Code with an active subscription (Pro/Max)
- Must be logged in (`/login` in Claude Code)

## Inspired By

- [quotapulse](https://github.com/chaoxu/quotapulse) — Multi-provider CLI usage tracker (Codex/Claude/Gemini). Great concept, but Node.js `fetch` doesn't respect system proxies on Windows, causing HTTP 403 errors behind Clash/V2Ray. This project solves that with Python `urllib`.

## License

MIT

---

[![Star History Chart](https://api.star-history.com/svg?repos=24kchengYe/claude-code-usage-monitor&type=Date)](https://star-history.com/#24kchengYe/claude-code-usage-monitor&Date)
