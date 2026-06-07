"""TeamTalk manager for handling communication with the bot worker process."""

import asyncio
import uuid
from multiprocessing import Process, Queue
from typing import Any

from .config import RESPONSE_POLL_INTERVAL, RESPONSE_TIMEOUT_SECONDS, STARTUP_DELAY_SECONDS
from .logging_config import get_logger
from .tt_bot import teamtalk_worker

logger = get_logger("manager")


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

        # Clean up dead process if any
        if self.process is not None:
            try:
                self.process.terminate()
                self.process.join(timeout=2)
            except Exception:
                pass

        self.request_queue = Queue()
        self.response_queue = Queue()
        self.process = Process(
            target=teamtalk_worker,
            args=(self.request_queue, self.response_queue),
            daemon=True,
        )
        self.process.start()
        await asyncio.sleep(STARTUP_DELAY_SECONDS)

    def _is_alive(self) -> bool:
        return self.process is not None and self.process.is_alive()

    async def _ensure_alive(self) -> bool:
        """Restart worker if it has died. Returns True if alive after check."""
        if not self._is_alive():
            logger.warning("Worker process is dead – restarting…")
            await self.start()
        return self._is_alive()

    async def _send_request(self, payload: dict[str, Any], timeout: float | None = None) -> dict[str, Any] | None:
        """Send a request and wait for the correlated response.

        A unique ``request_id`` is added to every outgoing message so that
        stale or orphan responses left in the queue from a previous call or a
        dead process cannot be mistakenly consumed by the current caller.
        """
        async with self._lock:
            if not await self._ensure_alive():
                return {"error": "Worker could not be started"}

            request_id = str(uuid.uuid4())
            payload["request_id"] = request_id
            self.request_queue.put(payload)

            effective_timeout = timeout if timeout is not None else RESPONSE_TIMEOUT_SECONDS
            iterations = int(effective_timeout / RESPONSE_POLL_INTERVAL)

            for _ in range(iterations):
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    # Accept only the response that matches our request_id.
                    # Drop everything else (stale responses from dead requests).
                    resp_id = response.get("request_id")
                    if resp_id is None or resp_id == request_id:
                        return response
                    # It's someone else's orphan – discard and keep waiting.
                    logger.debug("Discarded orphan response with id=%s (waiting for %s)", resp_id, request_id)

            logger.warning("Timeout waiting for response to action=%s", payload.get("action"))
            return None

    # ------------------------------------------------------------------ #
    #  Public API – each method just calls _send_request                  #
    # ------------------------------------------------------------------ #

    async def check_user_exists(self, username: str) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "check_user", "username": username})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("exists", False), resp.get("error")

    async def create_user(self, username: str, password: str) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "create_user", "username": username, "password": password})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def send_broadcast(self, message: str) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "broadcast", "message": message})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def authenticate_admin(self, username: str, password: str) -> tuple[bool, bool, str | None]:
        resp = await self._send_request({"action": "authenticate_admin", "username": username, "password": password})
        if resp is None:
            return False, False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("is_admin", False), resp.get("error")

    async def list_user_accounts(self) -> tuple[list[dict[str, Any]], str | None]:
        resp = await self._send_request({"action": "list_accounts"}, timeout=RESPONSE_TIMEOUT_SECONDS * 2)
        if resp is None:
            return [], "Timeout waiting for response"
        return resp.get("accounts", []), resp.get("error")

    async def get_online_users(self) -> tuple[list[dict[str, Any]], str | None]:
        resp = await self._send_request({"action": "get_online_users"})
        if resp is None:
            return [], "Timeout waiting for response"
        return resp.get("users", []), resp.get("error")

    async def send_private_message(self, user_id: int, message: str) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "send_private_message", "user_id": user_id, "message": message})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def send_channel_message(self, message: str) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "send_channel_message", "message": message})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def get_channel_messages(self) -> list[dict[str, Any]]:
        resp = await self._send_request({"action": "get_channel_messages"})
        if resp is None:
            return []
        return resp.get("messages", [])

    async def clear_channel_messages(self) -> None:
        await self._send_request({"action": "clear_channel_messages"})

    async def send_broadcast_message(self, message: str) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "send_broadcast_message", "message": message})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def get_channels(self) -> list[dict[str, Any]]:
        resp = await self._send_request({"action": "get_channels"})
        if resp is None:
            return []
        return resp.get("channels", [])

    async def join_channel(self, channel_id: int) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "join_channel", "channel_id": channel_id})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def leave_channel(self) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "leave_channel"})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def get_current_channel(self) -> int:
        resp = await self._send_request({"action": "get_current_channel"})
        if resp is None:
            return 0
        return resp.get("channel_id", 0)

    async def get_events(self) -> list[dict[str, Any]]:
        resp = await self._send_request({"action": "get_events"})
        if resp is None:
            return []
        return resp.get("events", [])

    async def clear_events(self) -> None:
        await self._send_request({"action": "clear_events"})

    async def kick_user(self, user_id: int) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "kick_user", "user_id": user_id})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def ban_user(self, user_id: int) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "ban_user", "user_id": user_id})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def ban_username(self, username: str) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "ban_username", "username": username})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def change_status(self, status_mode: int, status_message: str) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "change_status", "status_mode": status_mode, "status_message": status_message})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def get_status(self) -> tuple[int, str, str | None]:
        resp = await self._send_request({"action": "get_status"})
        if resp is None:
            return 0, "", "Timeout waiting for response"
        return resp.get("status_mode", 0), resp.get("status_message", ""), resp.get("error")

    async def queue_offline_pm(self, username: str, message: str) -> tuple[bool, str | None]:
        from .scheduler import task_scheduler
        await task_scheduler.queue_offline_pm(username, message, "Admin PM")
        return True, None

    async def stream_audio(self, file_path: str) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "stream_audio", "file_path": file_path})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    async def stop_audio(self) -> tuple[bool, str | None]:
        resp = await self._send_request({"action": "stop_audio"})
        if resp is None:
            return False, "Timeout waiting for response"
        return resp.get("success", False), resp.get("error")

    def stop(self) -> None:
        """Stop the TeamTalk worker process."""
        if self.request_queue is not None:
            try:
                self.request_queue.put({"action": "shutdown"})
            except Exception:
                pass
        if self.process is not None and self.process.is_alive():
            self.process.terminate()
            # join() is blocking – use a short timeout only; avoid blocking event loop
            self.process.join(timeout=3)


# Global manager instance
tt_manager = TeamTalkManager()
