#!/bin/bash
set -euo pipefail
cd /home/jidolstar/.openclaw/workspace/ai-briefings-clone
python3 scripts/collect_news.py
if git status --porcelain | grep -q '^'; then
  git add feeds.json README.md scripts daily monthly state logs
  if ! git diff --cached --quiet; then
    git commit -m "AI briefing $(date +%Y-%m-%d)"
    git push origin ai-briefings
  fi
fi
