#!/usr/bin/env bash
# Deploy/redeploy the Go ttserver on the VPS: install the Go toolchain on
# first run, pull the latest code, rebuild the binary, install the systemd
# unit, stop the legacy python ttbot (same 'bot' login as ttserver), and
# restart the service. Idempotent — safe to rerun for every redeploy.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x "$HOME/go-root/bin/go" ]; then
  echo "installing Go toolchain into ~/go-root ..."
  curl -fsSL -o /tmp/go.tgz https://go.dev/dl/go1.27.0.linux-amd64.tar.gz
  mkdir -p "$HOME/go-root"
  tar -C "$HOME/go-root" --strip-components=1 -xzf /tmp/go.tgz
  rm -f /tmp/go.tgz
fi
export PATH="$HOME/go-root/bin:$PATH"

echo "pulling latest code ..."
git pull --ff-only

# Merge the ntfy push settings from the legacy python ttbot config into the
# repo .env if they are not there yet. Keys keep working values; the ntfy
# password never leaves the server.
if [ -f "$HOME/ttbot/.env" ]; then
  while IFS= read -r line; do
    case "$line" in
      NTFY_*=*)
        key="${line%%=*}"
        grep -q "^$key=" .env || echo "$line" >> .env
        ;;
    esac
  done < "$HOME/ttbot/.env"
fi

echo "building ttserver ..."
(cd go && go build -o ../ttserver ./cmd/ttserver)

echo "installing systemd unit ..."
sudo install -m 644 deploy/ttserver.service /etc/systemd/system/ttserver.service
sudo systemctl daemon-reload

# The legacy python ntfy bot logs into TeamTalk as the same 'bot' account as
# ttserver; a second login would kick the first one off. Disable it for good.
if systemctl is-active --quiet ttbot.service; then
  echo "stopping and disabling legacy python ttbot.service ..."
  sudo systemctl disable --now ttbot.service || true
fi

echo "starting ttserver.service ..."
sudo systemctl enable ttserver.service
# enable --now only STARTS a stopped unit. On a redeploy the unit is already
# running, so without an explicit restart the freshly built binary never gets
# loaded and the old one keeps serving from memory.
sudo systemctl restart ttserver.service
sleep 1
sudo systemctl --no-pager status ttserver.service | head -14 || true
echo "DEPLOY OK"
