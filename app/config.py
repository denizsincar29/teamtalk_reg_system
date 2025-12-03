"""Application configuration settings."""

import os

# Application configuration constants
MIN_USERNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 4
RESPONSE_TIMEOUT_SECONDS = 10
RESPONSE_POLL_INTERVAL = 0.1
STARTUP_DELAY_SECONDS = 5

# Server configuration - credentials should be set via environment variables
SERVER_CONFIG = {
    "host": os.environ.get("TEAMTALK_HOST", "denizsincar.ru"),
    "tcp_port": int(os.environ.get("TEAMTALK_TCP_PORT", "10333")),
    "udp_port": int(os.environ.get("TEAMTALK_UDP_PORT", "10333")),
    "username": os.environ.get("TEAMTALK_USERNAME", "bot"),
    "password": os.environ.get("TEAMTALK_PASSWORD", ""),
}

# Web server configuration
APP_HOST = os.environ.get("APP_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("APP_PORT", "8000"))
