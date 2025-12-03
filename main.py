"""TeamTalk Registration System - FastAPI Web Application.

This application provides a web interface for registering users on a TeamTalk server.
It runs the pytalk-ex library in a separate process to avoid blocking the main thread.
"""

import asyncio
import html
import multiprocessing
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from multiprocessing import Process, Queue
from typing import Any

import pytalk
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pytalk import enums

# Server configuration - credentials should be set via environment variables
SERVER_CONFIG = {
    "host": os.environ.get("TEAMTALK_HOST", "denizsincar.ru"),
    "tcp_port": int(os.environ.get("TEAMTALK_TCP_PORT", "10333")),
    "udp_port": int(os.environ.get("TEAMTALK_UDP_PORT", "10333")),
    "username": os.environ.get("TEAMTALK_USERNAME", "bot"),
    "password": os.environ.get("TEAMTALK_PASSWORD", "893200"),
}


# HTML template for the registration form
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TeamTalk Registration</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 500px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .form-container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }}
        input[type="text"], input[type="password"] {{
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 16px;
        }}
        input[type="text"]:focus, input[type="password"]:focus {{
            outline: none;
            border-color: #4CAF50;
        }}
        button {{
            width: 100%;
            padding: 14px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        }}
        button:hover {{
            background-color: #45a049;
        }}
        .message {{
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .success {{
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        .error {{
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
    </style>
</head>
<body>
    <div class="form-container">
        <h1>TeamTalk Registration</h1>
        {message}
        <form method="post" action="/register">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required 
                       placeholder="Enter your username">
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required 
                       placeholder="Enter your password">
            </div>
            <button type="submit">Register</button>
        </form>
    </div>
</body>
</html>
"""


def teamtalk_worker(request_queue: Queue, response_queue: Queue) -> None:
    """Worker function that runs in a separate process to handle TeamTalk operations.
    
    Args:
        request_queue: Queue to receive requests from the main process.
        response_queue: Queue to send responses back to the main process.
    """
    bot = pytalk.TeamTalkBot()
    instance_holder: dict[str, Any] = {"instance": None, "ready": False}

    async def process_requests() -> None:
        """Process incoming requests from the queue."""
        while True:
            await asyncio.sleep(0.1)
            
            if not instance_holder["ready"]:
                continue
                
            try:
                if not request_queue.empty():
                    request = request_queue.get_nowait()
                    action = request.get("action")
                    instance = instance_holder["instance"]
                    
                    if action == "check_user":
                        username = request.get("username")
                        try:
                            if instance is None:
                                response_queue.put({"exists": False, "error": "Not connected"})
                                continue
                            accounts = await instance.list_user_accounts()
                            exists = any(
                                str(acc.username).lower() == username.lower()
                                for acc in accounts
                            )
                            response_queue.put({"exists": exists})
                        except Exception as e:
                            response_queue.put({"exists": False, "error": str(e)})
                    
                    elif action == "create_user":
                        username = request.get("username")
                        password = request.get("password")
                        try:
                            if instance is None:
                                response_queue.put({"success": False, "error": "Not connected"})
                                continue
                            instance.create_user_account(
                                username,
                                password,
                                enums.UserType.DEFAULT
                            )
                            response_queue.put({"success": True})
                        except Exception as e:
                            response_queue.put({"success": False, "error": str(e)})
                    
                    elif action == "shutdown":
                        break
            except Exception:
                pass

    @bot.event
    async def on_ready() -> None:
        server_info = pytalk.TeamTalkServerInfo(SERVER_CONFIG)
        await bot.add_server(server_info)
        # Start the request processor after bot is ready
        bot.loop.create_task(process_requests())

    @bot.event
    async def on_my_login(srv: pytalk.server.Server) -> None:
        instance_holder["instance"] = srv.teamtalk_instance
        instance_holder["ready"] = True

    @bot.event
    async def on_error(ename: str, *args: Any, **kwargs: Any) -> None:
        response_queue.put({"error": f"TeamTalk error in {ename}: {args}"})

    bot.run()


class TeamTalkManager:
    """Manages communication with the TeamTalk worker process."""
    
    def __init__(self) -> None:
        self.request_queue: Queue | None = None
        self.response_queue: Queue | None = None
        self.process: Process | None = None
        self._lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Start the TeamTalk worker process."""
        if self.process is not None and self.process.is_alive():
            return
        
        self.request_queue = Queue()
        self.response_queue = Queue()
        self.process = Process(
            target=teamtalk_worker,
            args=(self.request_queue, self.response_queue),
            daemon=True
        )
        self.process.start()
        # Give the worker time to connect
        await asyncio.sleep(5)
    
    async def check_user_exists(self, username: str) -> tuple[bool, str | None]:
        """Check if a user already exists on the server.
        
        Args:
            username: The username to check.
            
        Returns:
            A tuple of (exists, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return False, "Worker not started"
            
            self.request_queue.put({"action": "check_user", "username": username})
            
            # Wait for response with timeout
            for _ in range(100):  # 10 second timeout
                await asyncio.sleep(0.1)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("exists", False), response.get("error")
            
            return False, "Timeout waiting for response"
    
    async def create_user(self, username: str, password: str) -> tuple[bool, str | None]:
        """Create a new user on the server.
        
        Args:
            username: The username for the new account.
            password: The password for the new account.
            
        Returns:
            A tuple of (success, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return False, "Worker not started"
            
            self.request_queue.put({
                "action": "create_user",
                "username": username,
                "password": password
            })
            
            # Wait for response with timeout
            for _ in range(100):  # 10 second timeout
                await asyncio.sleep(0.1)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("success", False), response.get("error")
            
            return False, "Timeout waiting for response"
    
    def stop(self) -> None:
        """Stop the TeamTalk worker process."""
        if self.request_queue is not None:
            self.request_queue.put({"action": "shutdown"})
        if self.process is not None and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=5)


# Global manager instance
tt_manager = TeamTalkManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    # Startup
    await tt_manager.start()
    yield
    # Shutdown
    tt_manager.stop()


app = FastAPI(title="TeamTalk Registration System", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    """Render the registration form."""
    return HTML_TEMPLATE.format(message="")


@app.post("/register", response_class=HTMLResponse)
async def register(
    username: str = Form(...),
    password: str = Form(...)
) -> str:
    """Handle user registration.
    
    Args:
        username: The desired username.
        password: The desired password.
        
    Returns:
        HTML response with success or error message.
    """
    # Validate input
    if not username or not password:
        message = '<div class="message error">Username and password are required.</div>'
        return HTML_TEMPLATE.format(message=message)
    
    if len(username) < 3:
        message = '<div class="message error">Username must be at least 3 characters.</div>'
        return HTML_TEMPLATE.format(message=message)
    
    if len(password) < 4:
        message = '<div class="message error">Password must be at least 4 characters.</div>'
        return HTML_TEMPLATE.format(message=message)
    
    # Check if user already exists
    exists, error = await tt_manager.check_user_exists(username)
    
    if error:
        escaped_error = html.escape(str(error))
        message = f'<div class="message error">Error checking user: {escaped_error}</div>'
        return HTML_TEMPLATE.format(message=message)
    
    if exists:
        message = '<div class="message error">Username already exists. Please choose another.</div>'
        return HTML_TEMPLATE.format(message=message)
    
    # Create the user
    success, error = await tt_manager.create_user(username, password)
    
    if success:
        escaped_username = html.escape(username)
        message = f'<div class="message success">User "{escaped_username}" registered successfully! You can now connect to the TeamTalk server.</div>'
        return HTML_TEMPLATE.format(message=message)
    else:
        escaped_error = html.escape(str(error))
        message = f'<div class="message error">Failed to create user: {escaped_error}</div>'
        return HTML_TEMPLATE.format(message=message)


if __name__ == "__main__":
    import uvicorn
    multiprocessing.set_start_method("spawn", force=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)
