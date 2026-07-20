#!/usr/bin/env python3
"""Extract the final review text + aggregate token usage from pi `--mode json`.

Usage: pi-extract-review.py <events.jsonl>
Prints the last assistant message text (the review) followed by a
`### Token Usage` section aggregated across the run's assistant turns.
"""

import json
import sys

final = ""
usage_total = {"input": 0, "output": 0, "reasoning": 0, "cacheRead": 0, "cacheWrite": 0}

try:
    with open(sys.argv[1]) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = evt.get("message") or {}
            if evt.get("type") == "message_end" and msg.get("role") == "assistant":
                for part in msg.get("content", []):
                    if part.get("type") == "text" and part.get("text", "").strip():
                        final = part["text"]
                u = msg.get("usage") or {}
                for key in usage_total:
                    val = u.get(key)
                    if isinstance(val, int | float):
                        usage_total[key] += int(val)
except (FileNotFoundError, IndexError):
    pass

lines = [
    final.strip() or "pi produced no review output.",
    "",
    "### Token Usage",
    "",
    f"Input tokens: `{usage_total['input']}`",
    f"Output tokens: `{usage_total['output']}`",
    f"Reasoning tokens: `{usage_total['reasoning']}`",
    f"Cache read tokens: `{usage_total['cacheRead']}`",
    f"Cache write tokens: `{usage_total['cacheWrite']}`",
    f"Total tokens: `{usage_total['input'] + usage_total['output'] + usage_total['cacheRead'] + usage_total['cacheWrite']}`",
]
print("\n".join(lines))
