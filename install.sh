#!/usr/bin/env bash
# install.sh — first-time setup for teamtalk-reg
#
# Run from the repo directory. Does:
#   1. Installs uv into ~/.local/bin if not already present
#   2. uv sync --no-dev (creates .venv in the repo dir)
#   3. Bootstraps .env from .env.example if missing
#   4. Creates data/ dir if missing
#   5. Creates /etc/systemd/system/<service>.service (needs sudo)
#        runs as current user, survives logout, no linger needed
#
# Usage:
#   ./install.sh           — service name: teamtalk-reg
#   ./install.sh mysvc     — custom service name

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE="${1:-teamtalk-reg}"
SERVICE_FILE="/etc/systemd/system/$SERVICE.service"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}==> teamtalk-reg install${NC}"
echo    "    dir    : $SCRIPT_DIR"
echo    "    service: $SERVICE"
echo    "    user   : $USER"
echo

# ── Preflight ──────────────────────────────────────────────────────────────────
if [[ ! -f "$SCRIPT_DIR/main.py" ]]; then
    echo -e "${RED}ERROR: run from the repo root (main.py not found)${NC}"
    exit 1
fi

# ── 1. Install uv ─────────────────────────────────────────────────────────────
if command -v uv &>/dev/null || [[ -x "$HOME/.local/bin/uv" ]]; then
    echo -e "${GREEN}  uv already installed${NC}"
else
    echo "  installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo -e "${GREEN}  uv installed at $HOME/.local/bin/uv${NC}"
fi
export PATH="$HOME/.local/bin:$PATH"
echo

# ── 2. Sync deps ───────────────────────────────────────────────────────────────
echo "  syncing Python deps..."
(cd "$SCRIPT_DIR" && uv sync --no-dev)
echo

# ── 3. Bootstrap .env ─────────────────────────────────────────────────────────
if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    if [[ -f "$SCRIPT_DIR/.env.example" ]]; then
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo -e "${YELLOW}  .env created from .env.example — edit it before starting!${NC}"
    else
        cat > "$SCRIPT_DIR/.env" << 'ENVEOF'
# TeamTalk server connection
TEAMTALK_HOST=localhost
TEAMTALK_TCP_PORT=10333
TEAMTALK_UDP_PORT=10333
TEAMTALK_USERNAME=bot
TEAMTALK_PASSWORD=

# Optional: connect bot to localhost even if TEAMTALK_HOST is a public address
USE_LOCALHOST_FOR_BOT=false

# Channel ID for the bot to sit in (0 = none, 1 = root)
BOT_JOIN_CHANNEL_ID=0

# Web server
APP_HOST=127.0.0.1
APP_PORT=8000

# Reverse proxy (leave blank if serving at domain root)
ROOT_PATH=
FORWARDED_ALLOW_IPS=127.0.0.1

# ntfy push notifications (leave blank to disable)
# Either set NTFY_URL directly:
NTFY_URL=
# Or set server + topic separately:
# NTFY_SERVER=https://ntfy.sh
# NTFY_TOPIC=my-teamtalk-topic
ENVEOF
        echo -e "${YELLOW}  .env created with defaults — edit $SCRIPT_DIR/.env before starting!${NC}"
    fi
else
    echo "  .env already exists — left untouched."
fi

# ── 4. Runtime dirs ────────────────────────────────────────────────────────────
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$SCRIPT_DIR/app/uploads"
echo

# ── 5. System-level systemd service (sudo) ────────────────────────────────────
echo "  writing $SERVICE_FILE (needs sudo)..."
sudo tee "$SERVICE_FILE" > /dev/null << UNITEOF
[Unit]
Description=TeamTalk Registration System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
EnvironmentFile=$SCRIPT_DIR/.env
ExecStart=$HOME/.local/bin/uv run python $SCRIPT_DIR/main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE

[Install]
WantedBy=multi-user.target
UNITEOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE"
echo -e "${GREEN}  service installed and enabled: $SERVICE${NC}"
echo

# ── Summary ───────────────────────────────────────────────────────────────────
echo -e "${GREEN}==> Install complete.${NC}"
echo
echo    "  Next steps:"
echo -e "    1. Edit config : ${CYAN}nano $SCRIPT_DIR/.env${NC}"
echo -e "    2. Start       : ${CYAN}sudo systemctl start $SERVICE${NC}"
echo -e "    3. Logs        : ${CYAN}journalctl -u $SERVICE -f${NC}"
echo
