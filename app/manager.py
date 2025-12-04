"""TeamTalk manager for handling communication with the bot worker process."""

import asyncio
from multiprocessing import Process, Queue
from typing import Any

from .config import RESPONSE_POLL_INTERVAL, RESPONSE_TIMEOUT_SECONDS, STARTUP_DELAY_SECONDS
from .tt_bot import teamtalk_worker


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
        await asyncio.sleep(STARTUP_DELAY_SECONDS)
    
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
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
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
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("success", False), response.get("error")
            
            return False, "Timeout waiting for response"
    
    async def send_broadcast(self, message: str) -> tuple[bool, str | None]:
        """Send a broadcast message to all users on the server.
        
        Args:
            message: The message to broadcast.
            
        Returns:
            A tuple of (success, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return False, "Worker not started"
            
            self.request_queue.put({
                "action": "broadcast",
                "message": message
            })
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("success", False), response.get("error")
            
            return False, "Timeout waiting for response"
    
    async def authenticate_admin(self, username: str, password: str) -> tuple[bool, bool, str | None]:
        """Authenticate a user and check if they are an admin.
        
        Args:
            username: The username to authenticate.
            password: The password to authenticate.
            
        Returns:
            A tuple of (success, is_admin, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return False, False, "Worker not started"
            
            self.request_queue.put({
                "action": "authenticate_admin",
                "username": username,
                "password": password
            })
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("success", False), response.get("is_admin", False), response.get("error")
            
            return False, False, "Timeout waiting for response"
    
    async def list_user_accounts(self) -> tuple[list[dict[str, Any]], str | None]:
        """List all user accounts on the server.
        
        Returns:
            A tuple of (accounts_list, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return [], "Worker not started"
            
            self.request_queue.put({"action": "list_accounts"})
            
            # Wait for response with longer timeout for account listing
            timeout = RESPONSE_TIMEOUT_SECONDS * 2
            iterations = int(timeout / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("accounts", []), response.get("error")
            
            return [], "Timeout waiting for response"
    
    async def get_online_users(self) -> tuple[list[dict[str, Any]], str | None]:
        """Get list of online users on the server.
        
        Returns:
            A tuple of (users_list, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return [], "Worker not started"
            
            self.request_queue.put({"action": "get_online_users"})
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("users", []), response.get("error")
            
            return [], "Timeout waiting for response"
    
    async def send_private_message(self, user_id: int, message: str) -> tuple[bool, str | None]:
        """Send a private message to a user.
        
        Args:
            user_id: The ID of the user to send the message to.
            message: The message to send.
            
        Returns:
            A tuple of (success, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return False, "Worker not started"
            
            self.request_queue.put({
                "action": "send_private_message",
                "user_id": user_id,
                "message": message
            })
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("success", False), response.get("error")
            
            return False, "Timeout waiting for response"
    
    async def send_channel_message(self, message: str) -> tuple[bool, str | None]:
        """Send a message to the channel the bot is currently in.
        
        Args:
            message: The message to send.
            
        Returns:
            A tuple of (success, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return False, "Worker not started"
            
            self.request_queue.put({
                "action": "send_channel_message",
                "message": message
            })
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("success", False), response.get("error")
            
            return False, "Timeout waiting for response"
    
    async def get_channel_messages(self) -> list[dict[str, Any]]:
        """Get channel messages collected by the bot.
        
        Returns:
            A list of message dictionaries.
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return []
            
            self.request_queue.put({"action": "get_channel_messages"})
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("messages", [])
            
            return []
    
    async def clear_channel_messages(self) -> None:
        """Clear all collected channel messages."""
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return
            
            self.request_queue.put({"action": "clear_channel_messages"})
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    self.response_queue.get_nowait()
                    return
    
    async def send_broadcast_message(self, message: str) -> tuple[bool, str | None]:
        """Send a broadcast message to all users on the server.
        
        Args:
            message: The message to broadcast.
            
        Returns:
            A tuple of (success, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return False, "Worker not started"
            
            self.request_queue.put({
                "action": "send_broadcast_message",
                "message": message
            })
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("success", False), response.get("error")
            
            return False, "Timeout waiting for response"
    
    async def get_channels(self) -> list[dict[str, Any]]:
        """Get list of all channels on the server.
        
        Returns:
            A list of channel dictionaries with id, name, path, has_password, parent_id.
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return []
            
            self.request_queue.put({"action": "get_channels"})
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("channels", [])
            
            return []
    
    async def join_channel(self, channel_id: int) -> tuple[bool, str | None]:
        """Make the bot join a channel.
        
        Args:
            channel_id: The ID of the channel to join.
            
        Returns:
            A tuple of (success, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return False, "Worker not started"
            
            self.request_queue.put({
                "action": "join_channel",
                "channel_id": channel_id
            })
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("success", False), response.get("error")
            
            return False, "Timeout waiting for response"
    
    async def leave_channel(self) -> tuple[bool, str | None]:
        """Make the bot leave its current channel.
        
        Returns:
            A tuple of (success, error_message).
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return False, "Worker not started"
            
            self.request_queue.put({"action": "leave_channel"})
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("success", False), response.get("error")
            
            return False, "Timeout waiting for response"
    
    async def get_current_channel(self) -> int:
        """Get the ID of the channel the bot is currently in.
        
        Returns:
            Channel ID, or 0 if not in a channel.
        """
        async with self._lock:
            if self.request_queue is None or self.response_queue is None:
                return 0
            
            self.request_queue.put({"action": "get_current_channel"})
            
            # Wait for response with timeout
            iterations = int(RESPONSE_TIMEOUT_SECONDS / RESPONSE_POLL_INTERVAL)
            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    return response.get("channel_id", 0)
            
            return 0
    
    def stop(self) -> None:
        """Stop the TeamTalk worker process."""
        if self.request_queue is not None:
            self.request_queue.put({"action": "shutdown"})
        if self.process is not None and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=5)


# Global manager instance
tt_manager = TeamTalkManager()
