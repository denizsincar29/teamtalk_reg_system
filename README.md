# TeamTalk Registration System

A FastAPI web application that allows users to register on a TeamTalk server.

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

## Project Structure

```
teamtalk_reg_system/
├── main.py              # Application entry point
├── app/
│   ├── __init__.py      # Package initialization
│   ├── config.py        # Configuration settings
│   ├── i18n.py          # Internationalization (Russian/English translations)
│   ├── tt_bot.py        # TeamTalk bot worker
│   ├── tt_file.py       # .tt file generation utilities
│   ├── manager.py       # TeamTalk manager for process communication
│   ├── routes.py        # FastAPI routes
│   ├── templates/
│   │   ├── base.html    # Registration form template
│   │   └── success.html # Success page template
│   └── static/
│       └── style.css    # CSS styles
├── pyproject.toml       # Project dependencies
└── README.md
```

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
| `TEAMTALK_HOST` | `denizsincar.ru` | TeamTalk server hostname |
| `TEAMTALK_TCP_PORT` | `10333` | TeamTalk TCP port |
| `TEAMTALK_UDP_PORT` | `10333` | TeamTalk UDP port |
| `TEAMTALK_USERNAME` | `bot` | Bot username for server connection |
| `TEAMTALK_PASSWORD` | (required) | Bot password for server connection |
| `APP_HOST` | `0.0.0.0` | Web server bind address (all IPs) |
| `APP_PORT` | `8000` | Web server port |
| `FORWARDED_ALLOW_IPS` | `*` | Allowed proxy IPs for X-Forwarded headers |
| `ROOT_PATH` | (empty) | URL path prefix for reverse proxy with subpath (e.g., `/myapp`) |

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

## Architecture

The application uses a multiprocessing approach because the pytalk-ex library runs a blocking event loop. The main FastAPI process communicates with a worker process that handles TeamTalk operations:

1. **Main Process**: Runs FastAPI/Uvicorn web server
2. **Worker Process**: Runs pytalk-ex bot that connects to the TeamTalk server

Communication between processes happens via multiprocessing Queues.

### Modules

- **config.py**: Contains all configuration constants and environment variable loading
- **tt_bot.py**: TeamTalk bot worker that handles server connections and user operations
- **tt_file.py**: Generates .tt configuration files and tt:// URLs
- **manager.py**: Manages communication between FastAPI and the TeamTalk worker process
- **routes.py**: FastAPI route handlers for the registration form

## Development

The original task description:

> Create a fastapi web application that registers users on my teamtalk server denizsincar.ru.
> It must receive a username and password from entered form data and register the user on the teamtalk server using the TeamTalk SDK.
> The pytalk-ex library doesn't like other frameworks, so we can run teamtalk things in a separate process.
> Also the website must check if this user already exists on the teamtalk server before registering.