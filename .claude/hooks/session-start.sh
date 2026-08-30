#!/bin/bash
set -euo pipefail

# Only run this setup in Claude Code on the web / remote sessions.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# This repo has no package manifest (no requirements.txt/pyproject.toml).
# Install the third-party Python packages the scripts actually import,
# so tools like archive-viewer/ask_archive.py or archive_mcp.py can run.
python3 -m pip install --user --quiet numpy httpx anthropic mcp cffi
