#!/bin/bash
# Starts the archive connector (read-only, port 8766) and opens a public
# tunnel to it with cloudflared, so an outside AI (Grok, Gemini, ChatGPT)
# can reach it. Prints the public URL when it's ready.
#
# Say the word and it stops: press Ctrl+C, or run stop_the_well.sh.

set -e
cd "/Users/saba/Desktop/Saba Code/archive-viewer"

if ! curl -s -m 2 -o /dev/null http://127.0.0.1:8766/health; then
  echo "Starting the connector on 8766..."
  nohup python3 connector.py > /tmp/archive_connector.log 2>&1 &
  sleep 2
else
  echo "Connector already running on 8766."
fi

echo "Opening the tunnel..."
cloudflared tunnel --url http://127.0.0.1:8766 > /tmp/cloudflared_well.log 2>&1 &
TUNNEL_PID=$!
echo "$TUNNEL_PID" > /tmp/cloudflared_well.pid

echo "Waiting for the public address..."
for i in $(seq 1 20); do
  URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' /tmp/cloudflared_well.log | head -1)
  if [ -n "$URL" ]; then
    echo ""
    echo "THE WELL IS OPEN:"
    echo "  $URL"
    echo ""
    echo "Paste that address, plus /openapi.json, into whichever AI you're giving the door to."
    echo "It stays read-only. Run stop_the_well.sh, or kill $TUNNEL_PID, to close it."
    exit 0
  fi
  sleep 1
done

echo "Tunnel is taking longer than expected — check /tmp/cloudflared_well.log"
