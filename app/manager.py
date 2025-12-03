"""TeamTalk manager for handling communication with the bot worker process."""

import asyncio
from multiprocessing import Process, Queue

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
    
    def stop(self) -> None:
        """Stop the TeamTalk worker process."""
        if self.request_queue is not None:
            self.request_queue.put({"action": "shutdown"})
        if self.process is not None and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=5)


# Global manager instance
tt_manager = TeamTalkManager()
