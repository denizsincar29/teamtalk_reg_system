"""TeamTalk bot worker that runs in a separate process."""

import asyncio
from multiprocessing import Queue
from typing import Any

import pytalk
from pytalk import enums

from .config import BOT_SERVER_CONFIG


def teamtalk_worker(request_queue: Queue, response_queue: Queue) -> None:
    """Worker function that runs in a separate process to handle TeamTalk operations.
    
    Args:
        request_queue: Queue to receive requests from the main process.
        response_queue: Queue to send responses back to the main process.
    """
    bot = pytalk.TeamTalkBot()
    instance_holder: dict[str, Any] = {"instance": None, "server": None, "ready": False}

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
                    server = instance_holder["server"]
                    
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
                            # Send broadcast message announcing new user registration
                            if server is not None:
                                try:
                                    server.send_message(
                                        f"New user registered: {username}"
                                    )
                                except Exception:
                                    # Don't fail registration if broadcast fails
                                    pass
                            response_queue.put({"success": True})
                        except Exception as e:
                            response_queue.put({"success": False, "error": str(e)})
                    
                    elif action == "broadcast":
                        message = request.get("message")
                        try:
                            if server is None:
                                response_queue.put({"success": False, "error": "Not connected"})
                                continue
                            server.send_message(message)
                            response_queue.put({"success": True})
                        except Exception as e:
                            response_queue.put({"success": False, "error": str(e)})
                    
                    elif action == "shutdown":
                        break
            except Exception:
                pass

    @bot.event
    async def on_ready() -> None:
        server_info = pytalk.TeamTalkServerInfo(BOT_SERVER_CONFIG)
        await bot.add_server(server_info)
        # Start the request processor after bot is ready
        bot.loop.create_task(process_requests())

    @bot.event
    async def on_my_login(srv: pytalk.server.Server) -> None:
        instance_holder["instance"] = srv.teamtalk_instance
        instance_holder["server"] = srv
        instance_holder["ready"] = True

    @bot.event
    async def on_error(ename: str, *args: Any, **kwargs: Any) -> None:
        response_queue.put({"error": f"TeamTalk error in {ename}: {args}"})

    bot.run()
