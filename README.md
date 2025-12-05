# TeamTalk Registration System

A FastAPI web application that allows users to register on a TeamTalk server.

**Created by Deniz Sincar ([denizsincar.ru](https://denizsincar.ru))**

## Features

- Clean, responsive HTML registration form
- **Multi-language support** (Russian and English)
- Input validation (minimum username and password lengths)
- Checks if user already exists before registration
- Creates new user accounts on the TeamTalk server
- Broadcasts a message when a new user registers
- **After registration success page with:**
  - Downloadable .tt configuration file
  - tt:// URL for direct connection
  - Server connection details
- Test broadcast endpoint (`/api/broadcast`)
- XSS protection with HTML escaping
- Configurable via environment variables

## Requirements

- Python 3.13+
- UV package manager
- libpulse library (for the TeamTalk SDK)

### Installing libpulse on Ubuntu/Debian

```bash
sudo apt install libpulse0
```

## Installation

1. Install dependencies:
```bash
uv sync
```

## Configuration

Configuration can be set via environment variables or a `.env` file in the project root.

1. Copy the example configuration:
```bash
cp .env.example .env
```

2. Edit `.env` with your settings:
```bash
nano .env
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEAMTALK_HOST` | `localhost` | TeamTalk server hostname (used in .tt files for end users) |
| `TEAMTALK_TCP_PORT` | `10333` | TeamTalk TCP port |
| `TEAMTALK_UDP_PORT` | `10333` | TeamTalk UDP port |
| `TEAMTALK_USERNAME` | `bot` | Bot username for server connection |
| `TEAMTALK_PASSWORD` | (required) | Bot password for server connection |
| `TEAMTALK_NICKNAME` | (username) | Bot nickname (display name shown to other users) |
| `USE_LOCALHOST_FOR_BOT` | `false` | If true, bot connects to localhost instead of TEAMTALK_HOST |
| `APP_HOST` | `0.0.0.0` | Web server bind address (all IPs) |
| `APP_PORT` | `8000` | Web server port |
| `FORWARDED_ALLOW_IPS` | `*` | Allowed proxy IPs for X-Forwarded headers |
| `ROOT_PATH` | (empty) | URL path prefix for reverse proxy with subpath (e.g., `/myapp`) |

### Bot Connection Settings

When `USE_LOCALHOST_FOR_BOT` is set to `true`, the bot will connect to the TeamTalk server using `localhost` instead of the `TEAMTALK_HOST` value. This is useful when running the web application on the same machine as the TeamTalk server.

The `.tt` configuration files and `tt://` URLs generated for users will still use the `TEAMTALK_HOST` value, ensuring users can connect from external networks.

## Running the Application

```bash
# Run the application (reads from .env automatically)
uv run main.py
```

Then open http://localhost:8000 in your browser.

## Apache Reverse Proxy Setup

To run this application behind an Apache reverse proxy:

### Option 1: Proxy at root (example.com)

```apache
<VirtualHost *:80>
    ServerName example.com
    
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
    
    RequestHeader set X-Forwarded-Proto "http"
    RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}s"
</VirtualHost>
```

### Option 2: Proxy at subpath (example.com/teamtalk)

```apache
<VirtualHost *:80>
    ServerName example.com
    
    ProxyPreserveHost On
    ProxyPass /teamtalk http://127.0.0.1:8000
    ProxyPassReverse /teamtalk http://127.0.0.1:8000
    
    RequestHeader set X-Forwarded-Proto "http"
    RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}s"
</VirtualHost>
```

For subpath proxying, set `ROOT_PATH=/teamtalk` in your `.env` file.

**Required Apache modules:**
```bash
sudo a2enmod proxy proxy_http headers
sudo systemctl restart apache2
```

## Usage

1. Navigate to the registration page
2. Enter a username (minimum 3 characters)
3. Enter a password (minimum 4 characters)  
4. Click "Register"
5. On success, you'll see a page with:
   - Download link for a .tt configuration file
   - tt:// URL link for direct connection
   - Server connection details
6. Use either method to connect to the TeamTalk server

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Registration form |
| `/register` | POST | Handle registration |
| `/download-tt/{username}/{password_encoded}` | GET | Download .tt file |
| `/api/broadcast` | GET | Send test broadcast message |

## Admin Panel

The application includes a full-featured admin panel accessible at `/admin`. Administrators can log in using their TeamTalk admin credentials.

### Admin Features

| Feature | Description |
|---------|-------------|
| **User Management** | View online users, list all accounts, kick/ban users |
| **Chat** | Send broadcast messages, private messages, and channel messages |
| **Server Control** | View channels, manage scheduler, change bot status |
| **Scheduler** | Schedule automated tasks (broadcasts, status changes, login messages) |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Alt+1 | Switch to Users tab |
| Alt+2 | Switch to Chat tab |
| Alt+3 | Switch to Server tab |

### User Management Actions

- **Online Users**: View real-time list of connected users with kick/ban buttons
- **Accounts**: View all registered accounts with ban button
- **Click on user**: Opens Chat tab with `@username` prefilled for private messaging

### Bot Status

Administrators can change the bot's status mode (Online/Away/Question) and status message from the Server tab.

### Scheduler Task Types

| Task Type | Description |
|-----------|-------------|
| Broadcast | Send message to all users |
| Channel Message | Send message to a specific channel |
| PM (if online) | Send private message if user is online |
| On User Login | Send message when user logs in (with optional delay) |
| Status Change | Change bot status mode and message |

### Offline Private Messages

When sending a PM to an offline user via the Chat tab, the message is automatically queued and delivered when the user logs in.

## Architecture

The application uses a multiprocessing approach because the pytalk-ex library runs a blocking event loop. The main FastAPI process communicates with a worker process that handles TeamTalk operations:

1. **Main Process**: Runs FastAPI/Uvicorn web server
2. **Worker Process**: Runs pytalk-ex bot that connects to the TeamTalk server

Communication between processes happens via multiprocessing Queues.

## License

This project is open source. Created by Deniz Sincar ([denizsincar.ru](https://denizsincar.ru)).