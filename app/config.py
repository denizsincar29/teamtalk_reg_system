"""Application configuration settings.

All configuration is loaded from environment variables.
You can set these in a .env file in the project root.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Application configuration constants
MIN_USERNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 4
RESPONSE_TIMEOUT_SECONDS = 10
RESPONSE_POLL_INTERVAL = 0.1
STARTUP_DELAY_SECONDS = 5

# Server configuration - credentials should be set via environment variables or .env file
SERVER_CONFIG = {
    "host": os.environ.get("TEAMTALK_HOST", "denizsincar.ru"),
    "tcp_port": int(os.environ.get("TEAMTALK_TCP_PORT", "10333")),
    "udp_port": int(os.environ.get("TEAMTALK_UDP_PORT", "10333")),
    "username": os.environ.get("TEAMTALK_USERNAME", "bot"),
    "password": os.environ.get("TEAMTALK_PASSWORD", ""),
}

# Web server configuration
APP_HOST = os.environ.get("APP_HOST", "0.0.0.0")  # Allow all IPs by default
APP_PORT = int(os.environ.get("APP_PORT", "8000"))

# Proxy settings for Apache/Nginx reverse proxy
PROXY_HEADERS = True  # Enable reading X-Forwarded-* headers
FORWARDED_ALLOW_IPS = os.environ.get("FORWARDED_ALLOW_IPS", "*")  # Allow all proxy IPs

# Root path for reverse proxy with subpath (e.g., "/myapp" if proxied at example.com/myapp)
ROOT_PATH = os.environ.get("ROOT_PATH", "")
