---
name: usage-monitor
description: "Monitor Claude Code subscription usage and rate limits in real-time. Shows 5-hour and 7-day quota usage, reset countdowns, model-specific usage (Sonnet/Opus), and extra billing. Works as both a statusline widget and an on-demand skill. Use this skill when the user mentions: /usage, 查看用量, check usage, rate limit, 额度查询, show usage, 还剩多少额度, 用了多少, how much quota, usage report, 用量报告, 额度监控, 订阅用量, subscription usage, quota check, 剩余额度, remaining quota"
---

# Claude Code Usage Monitor

Monitor your Claude Code subscription usage directly inside Claude Code.

## Quick Check

Run the usage monitor script to get a detailed report:

```bash
python "~/.claude/skills/usage-monitor/usage_monitor.py" --detailed --force
```

For compact one-line output:

```bash
python "~/.claude/skills/usage-monitor/usage_monitor.py" --force
```

For JSON output (programmatic use):

```bash
python "~/.claude/skills/usage-monitor/usage_monitor.py" --json --force
```

## What the Numbers Mean

- **5-Hour Window**: Short-term rolling usage. Hitting 100% triggers temporary rate limiting until the window slides.
- **7-Day Window**: Long-term rolling usage. Hitting 100% means week-long rate limiting.
- **Sonnet/Opus 7-Day**: Per-model breakdown (if applicable).
- **Extra Usage**: Pay-as-you-go overage charges (if enabled in account settings).
- **Resets in**: Countdown until the usage window resets.

## Notes

- Data is cached for 60 seconds. Use `--force` to bypass cache.
- Uses Python urllib which natively respects system proxy settings (`HTTPS_PROXY` etc.)
- Credentials are read from `~/.claude/.credentials.json` (created by Claude Code on login)
- No additional dependencies required — pure Python standard library
