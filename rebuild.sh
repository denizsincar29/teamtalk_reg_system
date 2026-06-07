#!/usr/bin/env bash
# rebuild.sh — sync source + deps and restart the teamtalk-reg service
#
# What it does:
#   • Copies source files to DEST with rsync (skips .env, data/, venv, git, etc.)
#   • Runs `uv sync` in DEST so the virtualenv is up to date
#   • Restarts the systemd service (name auto-derived or passed as $2)
#   • Creates data/ dir in DEST if missing
#
# Usage:
#   ./rebuild.sh                         — deploy to default target, restart default service
#   ./rebuild.sh /opt/teamtalk-reg       — custom deploy path
#   ./rebuild.sh /opt/teamtalk-reg mysvc — custom path + custom service name

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-/opt/teamtalk-reg}"
SERVICE="${2:-teamtalk-reg}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}==> teamtalk-reg rebuild${NC}"
echo    "    src    : $SCRIPT_DIR"
echo    "    dest   : $DEST"
echo    "    service: $SERVICE"
echo

# ── Preflight ──────────────────────────────────────────────────────────────────
if [[ ! -f "$SCRIPT_DIR/main.py" ]]; then
    echo -e "${RED}ERROR: run from repo root (main.py not found)${NC}"
    exit 1
fi

if ! command -v uv &>/dev/null; then
    echo -e "${RED}ERROR: uv not found — install it first (see install.sh)${NC}"
    exit 1
fi

# ── Create dest if needed ──────────────────────────────────────────────────────
if [[ ! -d "$DEST" ]]; then
    echo -e "${YELLOW}  creating $DEST${NC}"
    mkdir -p "$DEST"
fi

# ── Sync source files ──────────────────────────────────────────────────────────
# --checksum        only copy when content differs
# --delete          remove stale files no longer in src
# Excluded:
#   .env            — keep live config untouched
#   data/           — persistent runtime data (scheduled tasks, offline PM queue)
#   .venv/          — managed by uv on the server
#   .git/           — not needed in deploy target
#   *.sh            — scripts stay in repo only
#   uploads/        — user-uploaded files, do not wipe

echo "  syncing source files..."
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

# Also sync uv.lock separately without --delete so it can be absent in dest
rsync -av --checksum \
    "$SCRIPT_DIR/uv.lock" "$DEST/uv.lock" 2>/dev/null || true

echo

# ── Ensure data directory exists ───────────────────────────────────────────────
if [[ ! -d "$DEST/data" ]]; then
    echo -e "${YELLOW}  creating $DEST/data/ (runtime persistence)${NC}"
    mkdir -p "$DEST/data"
fi

# ── Sync Python dependencies with uv ──────────────────────────────────────────
echo "  syncing Python deps with uv..."
(cd "$DEST" && uv sync --no-dev)
echo

# ── Restart systemd service ────────────────────────────────────────────────────
if systemctl --user is-active --quiet "$SERVICE" 2>/dev/null || \
   systemctl --user is-enabled --quiet "$SERVICE" 2>/dev/null; then
    echo "  restarting user service: $SERVICE"
    systemctl --user restart "$SERVICE"
    echo -e "${GREEN}  service restarted.${NC}"
elif systemctl is-active --quiet "$SERVICE" 2>/dev/null || \
     systemctl is-enabled --quiet "$SERVICE" 2>/dev/null; then
    echo "  restarting system service: $SERVICE (needs sudo)"
    sudo systemctl restart "$SERVICE"
    echo -e "${GREEN}  service restarted.${NC}"
else
    echo -e "${YELLOW}  service '$SERVICE' not found — skipping restart.${NC}"
    echo    "  Run install.sh to create it, then start with:"
    echo    "    systemctl --user start $SERVICE"
fi

echo
echo -e "${GREEN}==> Done.${NC}"
