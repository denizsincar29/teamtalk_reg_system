#!/usr/bin/env bash
# rebuild.sh — sync deps and restart the teamtalk-reg service
#
# Run from the repo directory. Does:
#   • uv sync --no-dev
#   • sudo systemctl restart teamtalk-reg (or custom service name)
#
# Usage:
#   ./rebuild.sh           — sync deps + restart default service
#   ./rebuild.sh mysvc     — sync deps + restart custom service name

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE="${1:-teamtalk-reg}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}==> teamtalk-reg rebuild${NC}"
echo    "    dir    : $SCRIPT_DIR"
echo    "    service: $SERVICE"
echo

if [[ ! -f "$SCRIPT_DIR/main.py" ]]; then
    echo -e "${RED}ERROR: run from the repo root (main.py not found)${NC}"
    exit 1
fi

export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv &>/dev/null; then
    echo -e "${RED}ERROR: uv not found — run install.sh first${NC}"
    exit 1
fi

# ── Sync deps ──────────────────────────────────────────────────────────────────
echo "  syncing Python deps..."
(cd "$SCRIPT_DIR" && uv sync --no-dev)
echo

# ── Restart service ────────────────────────────────────────────────────────────
if systemctl is-active --quiet "$SERVICE" 2>/dev/null || \
   systemctl is-enabled --quiet "$SERVICE" 2>/dev/null; then
    echo "  restarting service: $SERVICE"
    sudo systemctl restart "$SERVICE"
    echo -e "${GREEN}  done. Status: $(systemctl is-active "$SERVICE")${NC}"
else
    echo -e "${YELLOW}  service '$SERVICE' not found — skipping restart.${NC}"
    echo    "  Run install.sh to create it, then: sudo systemctl start $SERVICE"
fi

echo
echo -e "${GREEN}==> Done.${NC}"
