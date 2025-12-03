# TeamTalk Registration System

A FastAPI web application that allows users to register on a TeamTalk server.

## Features

- Clean, responsive HTML registration form
- Input validation (minimum username and password lengths)
- Checks if user already exists before registration
- Creates new user accounts on the TeamTalk server
- Broadcasts a message when a new user registers
- XSS protection with HTML escaping
- Configurable via environment variables

## Project Structure

```
teamtalk_reg_system/
├── main.py              # Application entry point
├── app/
│   ├── __init__.py      # Package initialization
│   ├── config.py        # Configuration settings
│   ├── tt_bot.py        # TeamTalk bot worker
│   ├── manager.py       # TeamTalk manager for process communication
│   ├── routes.py        # FastAPI routes
│   ├── templates/
│   │   └── base.html    # Jinja2 HTML template
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

Set the following environment variables (or use defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `TEAMTALK_HOST` | `denizsincar.ru` | TeamTalk server hostname |
| `TEAMTALK_TCP_PORT` | `10333` | TeamTalk TCP port |
| `TEAMTALK_UDP_PORT` | `10333` | TeamTalk UDP port |
| `TEAMTALK_USERNAME` | `bot` | Bot username for server connection |
| `TEAMTALK_PASSWORD` | (required) | Bot password for server connection |
| `APP_HOST` | `127.0.0.1` | Web server bind address |
| `APP_PORT` | `8000` | Web server port |

## Running the Application

```bash
# Set the TeamTalk password
export TEAMTALK_PASSWORD=your_bot_password

# Run the application
uv run main.py
```

Then open http://localhost:8000 in your browser.

## Usage

1. Navigate to the registration page
2. Enter a username (minimum 3 characters)
3. Enter a password (minimum 4 characters)  
4. Click "Register"
5. If successful, you can now connect to the TeamTalk server with your new credentials

## Architecture

The application uses a multiprocessing approach because the pytalk-ex library runs a blocking event loop. The main FastAPI process communicates with a worker process that handles TeamTalk operations:

1. **Main Process**: Runs FastAPI/Uvicorn web server
2. **Worker Process**: Runs pytalk-ex bot that connects to the TeamTalk server

Communication between processes happens via multiprocessing Queues.

### Modules

- **config.py**: Contains all configuration constants and environment variable loading
- **tt_bot.py**: TeamTalk bot worker that handles server connections and user operations
- **manager.py**: Manages communication between FastAPI and the TeamTalk worker process
- **routes.py**: FastAPI route handlers for the registration form

## Development

The original task description:

> Create a fastapi web application that registers users on my teamtalk server denizsincar.ru.
> It must receive a username and password from entered form data and register the user on the teamtalk server using the TeamTalk SDK.
> The pytalk-ex library doesn't like other frameworks, so we can run teamtalk things in a separate process.
> Also the website must check if this user already exists on the teamtalk server before registering.