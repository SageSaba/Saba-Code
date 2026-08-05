#!/bin/bash
# Closes the public tunnel opened by open_the_well.sh.
# The connector itself keeps running (still reachable from this Mac and
# the LAN) — only the public door closes. 8766 goes back to local-only.

if [ -f /tmp/cloudflared_well.pid ]; then
  PID=$(cat /tmp/cloudflared_well.pid)
  if kill "$PID" 2>/dev/null; then
    echo "Tunnel closed. The well is no longer public."
  else
    echo "No live tunnel found at that PID — it may already be closed."
  fi
  rm -f /tmp/cloudflared_well.pid
else
  pkill -f "cloudflared tunnel --url http://127.0.0.1:8766" 2>/dev/null \
    && echo "Tunnel closed." \
    || echo "No tunnel appears to be running."
fi
