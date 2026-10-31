# TeamTalk Registration System

A self-hosted web app that lets users register on a TeamTalk server: a public
registration form, a downloadable `.tt` config and `tt://` link, plus an admin
panel for users, channels and the bot.

**Created by Deniz Sincar ([denizsincar.ru](https://denizsincar.ru))**

The repository ships two implementations:

- **Go** (`go/`, recommended) — one static binary, no CGO, no `libpulse`,
  speaks the TeamTalk protocol itself. This is what production runs.
- **Python / FastAPI** (repository root) — the original version, kept as a
  reference. It needs Python 3.13, `uv` and the TeamTalk SDK with `libpulse`.

Both read the same `.env` and expose the same pages and endpoints.

## Features

- Clean, responsive registration form with Russian and English UI
- Input validation (minimum username and password lengths)
- Checks whether the account already exists before registering
- Creates accounts on the TeamTalk server and broadcasts a welcome message
- Success page with a downloadable `.tt` file and a `tt://` link
- `https://…/tturl?…` redirector, because messengers only link https URLs
- Admin panel: online users, accounts, kick/ban/delete, chat, channels, bot
  status, scheduler, queued offline private messages
- Configurable entirely through environment variables

## Go version — quick start

### Requirements

- Linux or macOS, Go 1.22 or newer (any CPU architecture — the binary is pure
  Go, `CGO_ENABLED=0` builds work)
- A reachable TeamTalk server and a bot account on it
- Optional: systemd + sudo for the `deploy.sh` path

### Build and run by hand

```bash
cp .env.example .env
nano .env                       # fill in TEAMTALK_* and the rest
cd go
go build -o ../ttserver ./cmd/ttserver
cd ..
set -a; . ./.env; set +a        # export the settings
./ttserver
```

The app listens on `APP_HOST:APP_PORT` (default `0.0.0.0:8000`). Scheduled
tasks and queued offline messages are stored in `DATA_DIR` (default `./data`);
the directory is created on first run.

### One-command deploy with systemd

```bash
bash deploy.sh
```

`deploy.sh` is idempotent and does the whole job:

1. installs the Go toolchain into `~/go-root` if it is missing — picking the
   tarball for this machine's architecture (`amd64`, `arm64`, `armv6l`);
2. `git pull --ff-only` when run inside a checkout;
3. creates `.env` from the example if there is none;
4. builds `./ttserver`;
5. renders `deploy/ttserver.service` for the current user and directory,
   installs it as `/etc/systemd/system/<name>.service` and restarts it.

Overrides: `GO_VERSION` (default `1.27.0`), `SERVICE_NAME` (default `ttserver`)
and `SERVICE_USER` (default: whoever runs the script), which is how you run the
service under a dedicated account. Passwordless `sudo` is required.

On a machine that also runs the legacy Python `ttbot.service`, `deploy.sh`
disables it: both log in as the same `bot` account and would kick each other
off.

### Reverse proxy

Caddy:

```caddy
tt.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

Nginx:

```nginx
server {
    listen 443 ssl;
    server_name tt.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

Apache works the same way with `ProxyPass / http://127.0.0.1:8000/`. The Go app
is served from the domain root; proxy it at the root rather than under a
subpath, and set `TT_SHORT_HOST` to the proxy hostname.

## Python version (legacy)

### Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- `libpulse` (the TeamTalk SDK links against it)

```bash
sudo apt install libpulse0     # Debian/Ubuntu
uv sync
cp .env.example .env           # fill in your values
uv run main.py
```

`install.sh` wraps the same steps and can install a systemd unit, but it is
Python-only; for the Go server use `deploy.sh`.

Architecture: `pytalk-ex` runs a blocking event loop, so the app uses two
processes — FastAPI/Uvicorn in the main process and a bot worker connected by
multiprocessing queues.

Apache reverse proxy at a subpath additionally needs `ROOT_PATH=/teamtalk` in
`.env`; see `install.sh` and the endpoints below.

## Configuration

Everything is read from environment variables, usually via a `.env` file in the
project root. The Go server reads the file through systemd's `EnvironmentFile`;
the Python app loads it itself.

| Variable | Default | Description |
|----------|---------|-------------|
| `TEAMTALK_HOST` | `localhost` | Public TeamTalk host used in `.tt` files and `tt://` URLs |
| `TEAMTALK_TCP_PORT` | `10333` | TeamTalk TCP port |
| `TEAMTALK_UDP_PORT` | `10333` | TeamTalk UDP port |
| `TEAMTALK_USERNAME` | `bot` | Bot account for the server connection |
| `TEAMTALK_PASSWORD` | (required) | Bot password |
| `TEAMTALK_NICKNAME` | (username) | Display name shown to other users |
| `USE_LOCALHOST_FOR_BOT` | `false` | Bot dials `localhost` instead of `TEAMTALK_HOST` |
| `BOT_JOIN_CHANNEL_ID` | `0` | Channel the bot joins after login; 0 = root |
| `APP_HOST` | `0.0.0.0` | Web listener bind address |
| `APP_PORT` | `8000` | Web listener port |
| `TT_SHORT_HOST` | `tt.<TEAMTALK_HOST>` | Host of the `/tturl` redirector |
| `ADMIN_TT_URL` | (empty) | `tt://` address a notification tap opens; empty = the bot account |
| `DATA_DIR` | `data` | Where scheduled tasks and the offline PM queue live |
| `NTFY_SERVER` | (empty) | ntfy base URL, e.g. `https://ntfy.sh` |
| `NTFY_TOPIC` | (empty) | ntfy topic |
| `NTFY_URL` | (empty) | Full ntfy URL; wins over server + topic |
| `NTFY_USERNAME` / `NTFY_PASSWORD` | (empty) | Basic auth for a protected ntfy server |
| `PRIVACY_URL` | (empty) | Link to your personal-data policy on the registration page |
| `PRIVACY_FILE` | (empty) | Plain-text policy file served at `/privacy` instead of `PRIVACY_URL` |
| `CONSENT_NOTE` | (empty) | Note stored in the TeamTalk account as proof of consent |
| `FORWARDED_ALLOW_IPS` | `*` | Python only — trusted proxy IPs |
| `ROOT_PATH` | (empty) | Python only — subpath prefix for reverse proxying |

Leaving all three ntfy keys empty disables push notifications; the bot then
works as a plain registration + admin service.

The personal-data consent step is optional and pluggable: point `PRIVACY_URL`
at your own policy page, or put a plain-text policy in a file and set
`PRIVACY_FILE` to serve it at `/privacy`. With neither set the registration
form simply has no consent checkbox and no policy link. `CONSENT_NOTE` sets
the wording written into each new TeamTalk account as proof of consent; when
it is empty the note is built from the policy link.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Registration form |
| `/register` | POST | Handle registration |
| `/download-tt/{username}/{password}` | GET | Download the `.tt` file |
| `/privacy` | GET | Local personal-data policy (only with `PRIVACY_FILE`) |
| `/tturl` | GET | https → `tt://` redirector for messengers |
| `/open` | GET | “Open in TeamTalk” helper page |
| `/admin` | GET | Admin panel (TeamTalk admin credentials) |
| `/api/broadcast` | GET | Test broadcast (Python app) |

## Admin panel

Available at `/admin`. Administrators log in with their TeamTalk admin
credentials; sessions are kept in memory with a rolling 30-day cookie, so a
restart of the service logs everyone out.

| Feature | Description |
|---------|-------------|
| **User management** | Online users, all accounts, kick, ban, unban, delete |
| **Chat** | Broadcast, private and channel messages |
| **Server control** | Channels, scheduler, bot status mode and message |
| **Scheduler** | Automated broadcasts, status changes and login messages |

Keyboard shortcuts: `Alt+1` users, `Alt+2` chat, `Alt+3` server.

Clicking an account opens the chat tab with `@username` prefilled. A private
message to an offline user is queued and delivered when they log in.

## License

This project is open source. Created by Deniz Sincar
([denizsincar.ru](https://denizsincar.ru)).
