#!/usr/bin/env bash
# Build and (re)deploy the Go ttserver.
#
# Works on any Linux host with systemd: installs the Go toolchain into
# ~/go-root on first run (matching the host CPU architecture), pulls the
# latest code when this is a git checkout, rebuilds the binary, renders the
# systemd unit for the current user and directory, and restarts the service.
# Idempotent — safe to rerun for every redeploy.
#
# Overridable environment:
#   GO_VERSION       Go release to install on first run (default 1.27.0)
#   SERVICE_NAME     systemd unit name without .service (default ttserver)
#   SERVICE_USER     account the service runs as (default: current user)
set -euo pipefail
cd "$(dirname "$0")"

GO_VERSION="${GO_VERSION:-1.27.0}"
SERVICE_NAME="${SERVICE_NAME:-ttserver}"
SERVICE_USER="${SERVICE_USER:-$(id -un)}"

case "$(uname -m)" in
  x86_64|amd64)  GO_ARCH=amd64 ;;
  aarch64|arm64) GO_ARCH=arm64 ;;
  armv7l|armv6l) GO_ARCH=armv6l ;;
  *)
    echo "unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

if [ ! -x "$HOME/go-root/bin/go" ]; then
  echo "installing Go $GO_VERSION ($GO_ARCH) into ~/go-root ..."
  curl -fsSL -o /tmp/go.tgz "https://go.dev/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz"
  mkdir -p "$HOME/go-root"
  tar -C "$HOME/go-root" --strip-components=1 -xzf /tmp/go.tgz
  rm -f /tmp/go.tgz
fi
export PATH="$HOME/go-root/bin:$PATH"

# A release tarball has no .git; only a real checkout can be pulled.
if [ -d .git ]; then
  echo "pulling latest code ..."
  git pull --ff-only
fi

if [ ! -f .env ]; then
  echo "no .env found — creating one from .env.example; fill in the TeamTalk credentials before the service can work" >&2
  cp .env.example .env
  chmod 600 .env
fi

# Merge the ntfy push settings from a legacy python ttbot config into the
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

echo "installing systemd unit $SERVICE_NAME.service (user=$SERVICE_USER, dir=$PWD) ..."
UNIT="$(mktemp)"
sed -e "s|@USER@|$SERVICE_USER|g" -e "s|@DIR@|$PWD|g" deploy/ttserver.service > "$UNIT"
sudo install -m 644 "$UNIT" "/etc/systemd/system/$SERVICE_NAME.service"
rm -f "$UNIT"
sudo systemctl daemon-reload

# The legacy python ntfy bot logs into TeamTalk as the same 'bot' account as
# ttserver; a second login would kick the first one off. Disable it if it is
# still running (nothing to do when this is a fresh self-hosted install).
if systemctl is-active --quiet ttbot.service 2>/dev/null; then
  echo "stopping and disabling legacy python ttbot.service ..."
  sudo systemctl disable --now ttbot.service || true
fi

echo "starting $SERVICE_NAME.service ..."
sudo systemctl enable "$SERVICE_NAME.service"
# enable --now only STARTS a stopped unit. On a redeploy the unit is already
# running, so without an explicit restart the freshly built binary never gets
# loaded and the old one keeps serving from memory.
sudo systemctl restart "$SERVICE_NAME.service"
sleep 1
sudo systemctl --no-pager status "$SERVICE_NAME.service" | head -14 || true
echo "DEPLOY OK"
