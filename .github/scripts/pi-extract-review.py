#!/usr/bin/env python3
"""Extract the final assistant review text from pi `--mode json` output.

Usage: pi-extract-review.py <events.jsonl>
Prints the last assistant message text (the review), or a fallback line.
"""

import json
import sys

final = ""
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
except (FileNotFoundError, IndexError):
    pass

print(final.strip() or "pi produced no review output.")
