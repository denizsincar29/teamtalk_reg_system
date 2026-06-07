#!/usr/bin/env bash
# install.sh — first-time setup for teamtalk-reg
#
# What it does:
#   1. Installs uv into ~/.local/bin if not already present
#   2. Deploys source files to DEST (same rsync logic as rebuild.sh)
#   3. Runs `uv sync` to create the virtualenv in DEST/.venv
#   4. Creates a .env from .env.example if none exists
#   5. Creates and enables a systemd --user service that runs:
#        ~/.local/bin/uv run python <DEST>/main.py
#
# Usage:
#   ./install.sh                         — install to default path with default service name
#   ./install.sh /opt/teamtalk-reg       — custom install path
#   ./install.sh /opt/teamtalk-reg mysvc — custom path + custom service name
#
# After install:
#   1. Edit $DEST/.env with your TeamTalk credentials
#   2. systemctl --user start teamtalk-reg
#   3. systemctl --user enable teamtalk-reg   (if not already enabled)
#   4. To allow the service to survive logout: loginctl enable-linger $USER

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-/opt/teamtalk-reg}"
SERVICE="${2:-teamtalk-reg}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}==> teamtalk-reg install${NC}"
echo    "    src    : $SCRIPT_DIR"
echo    "    dest   : $DEST"
echo    "    service: $SERVICE"
echo    "    user   : $USER"
echo

# ── 1. Install uv ─────────────────────────────────────────────────────────────
UV_BIN="$HOME/.local/bin/uv"

if command -v uv &>/dev/null; then
    echo -e "${GREEN}  uv already installed: $(command -v uv)${NC}"
elif [[ -x "$UV_BIN" ]]; then
    echo -e "${GREEN}  uv already installed: $UV_BIN${NC}"
else
    echo "  installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # The installer adds ~/.local/bin to PATH in shell rc files, but not this session
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "${GREEN}  uv installed at $UV_BIN${NC}"
fi

# Make sure uv is reachable for the rest of this script
export PATH="$HOME/.local/bin:$PATH"

if ! command -v uv &>/dev/null; then
    echo -e "${RED}ERROR: uv still not found after install — check $HOME/.local/bin is in PATH${NC}"
    exit 1
fi

echo

# ── 2. Deploy source files ─────────────────────────────────────────────────────
if [[ ! -d "$DEST" ]]; then
    echo -e "${YELLOW}  creating $DEST${NC}"
    mkdir -p "$DEST"
fi

echo "  syncing source files to $DEST..."
rsync -av --checksum --delete \
    --exclude='.env'           \
    --exclude='.env.*'         \
    --exclude='data/'          \
    --exclude='.venv/'         \
    --exclude='__pycache__/'   \
    --exclude='*.pyc'          \
    --exclude='.git/'          \
    --exclude='*.sh'           \
    --exclude='*.md'           \
    --exclude='app/uploads/'   \
    --exclude='uv.lock'        \
    "$SCRIPT_DIR/" "$DEST/"

rsync -av --checksum \
    "$SCRIPT_DIR/uv.lock" "$DEST/uv.lock" 2>/dev/null || true

echo

# ── 3. Create runtime dirs ─────────────────────────────────────────────────────
mkdir -p "$DEST/data"
mkdir -p "$DEST/app/uploads"

# ── 4. Bootstrap .env ─────────────────────────────────────────────────────────
if [[ ! -f "$DEST/.env" ]]; then
    if [[ -f "$SCRIPT_DIR/.env.example" ]]; then
        cp "$SCRIPT_DIR/.env.example" "$DEST/.env"
        echo -e "${YELLOW}  .env created from .env.example — edit $DEST/.env before starting!${NC}"
    else
        cat > "$DEST/.env" << 'ENVEOF'
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

# Reverse proxy settings (leave blank if not behind a subpath proxy)
ROOT_PATH=
FORWARDED_ALLOW_IPS=127.0.0.1
ENVEOF
        echo -e "${YELLOW}  .env created with defaults — edit $DEST/.env before starting!${NC}"
    fi
else
    echo    "  .env already exists — left untouched."
fi
echo

# ── 5. Install Python deps with uv ────────────────────────────────────────────
echo "  installing Python deps with uv..."
(cd "$DEST" && uv sync --no-dev)
echo

# ── 6. Create systemd user service ────────────────────────────────────────────
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/$SERVICE.service"

mkdir -p "$SERVICE_DIR"

echo "  writing $SERVICE_FILE..."
cat > "$SERVICE_FILE" << UNITEOF
[Unit]
Description=TeamTalk Registration System
After=network.target

[Service]
Type=simple
WorkingDirectory=$DEST
EnvironmentFile=$DEST/.env
ExecStart=$HOME/.local/bin/uv run python $DEST/main.py
Restart=on-failure
RestartSec=5
# Give the TeamTalk bot time to connect before the first request arrives
ExecStartPost=/bin/sleep 1

[Install]
WantedBy=default.target
UNITEOF

# Reload systemd user daemon and enable the service
systemctl --user daemon-reload
systemctl --user enable "$SERVICE"

echo -e "${GREEN}  service installed and enabled: $SERVICE${NC}"
echo

# ── 7. Linger hint ────────────────────────────────────────────────────────────
if ! loginctl show-user "$USER" 2>/dev/null | grep -q "Linger=yes"; then
    echo -e "${YELLOW}  NOTE: user linger is OFF.${NC}"
    echo    "  The service will stop when you log out."
    echo    "  To keep it running after logout:"
    echo -e "    ${CYAN}sudo loginctl enable-linger $USER${NC}"
    echo
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo -e "${GREEN}==> Install complete.${NC}"
echo
echo    "  Next steps:"
echo -e "    1. Edit config:  ${CYAN}nano $DEST/.env${NC}"
echo -e "    2. Start:        ${CYAN}systemctl --user start $SERVICE${NC}"
echo -e "    3. Check logs:   ${CYAN}journalctl --user -u $SERVICE -f${NC}"
echo -e "    4. Stop:         ${CYAN}systemctl --user stop $SERVICE${NC}"
echo
echo    "  To redeploy after changes:"
echo -e "    ${CYAN}./rebuild.sh${NC}"
echo
