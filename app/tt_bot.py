"""TeamTalk bot worker that runs in a separate process."""

import asyncio
from collections import deque
from datetime import datetime
from multiprocessing import Queue
from typing import Any

import pytalk
from pytalk import enums, Permission, message as tt_message

from .config import BOT_SERVER_CONFIG

# Default user rights for newly registered users
# This gives users standard capabilities: voice, messaging, file transfers, etc.
DEFAULT_USER_RIGHTS = (
    Permission.MULTI_LOGIN |           # Allow multiple simultaneous logins
    Permission.VIEW_ALL_USERS |        # See all users on the server
    Permission.CREATE_TEMPORARY_CHANNEL |  # Create temporary channels
    Permission.UPLOAD_FILES |          # Upload files to channels
    Permission.DOWNLOAD_FILES |        # Download files from channels
    Permission.TRANSMIT_VOICE |        # Transmit voice
    Permission.TRANSMIT_VIDEOCAPTURE | # Transmit video from camera
    Permission.TRANSMIT_DESKTOP |      # Share desktop
    Permission.TRANSMIT_MEDIAFILE_AUDIO |  # Stream audio files
    Permission.TRANSMIT_MEDIAFILE_VIDEO |  # Stream video files
    Permission.TEXTMESSAGE_USER |      # Send private messages
    Permission.TEXTMESSAGE_CHANNEL     # Send channel messages
)

# Maximum number of channel messages to store
MAX_CHANNEL_MESSAGES = 100


def teamtalk_worker(request_queue: Queue, response_queue: Queue) -> None:
    """Worker function that runs in a separate process to handle TeamTalk operations.
    
    Args:
        request_queue: Queue to receive requests from the main process.
        response_queue: Queue to send responses back to the main process.
    """
    bot = pytalk.TeamTalkBot()
    instance_holder: dict[str, Any] = {
        "instance": None,
        "server": None,
        "ready": False
    }
    # Store channel messages in a deque with max size
    channel_messages: deque[dict[str, Any]] = deque(maxlen=MAX_CHANNEL_MESSAGES)

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
                                enums.UserType.DEFAULT,
                                user_rights=DEFAULT_USER_RIGHTS
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
                    
                    elif action == "authenticate_admin":
                        username = request.get("username")
                        password = request.get("password")
                        try:
                            if instance is None:
                                response_queue.put({
                                    "success": False,
                                    "is_admin": False,
                                    "error": "Not connected"
                                })
                                continue
                            # Get all user accounts and check if user is admin
                            # Note: TeamTalk passwords may be hashed, so we check
                            # if the provided password matches the stored one
                            accounts = await instance.list_user_accounts()
                            is_admin = False
                            found = False
                            username_lower = username.lower()
                            for acc in accounts:
                                if str(acc.username).lower() == username_lower:
                                    found = True
                                    # Check if user type is admin
                                    if acc.user_type == enums.UserType.ADMIN:
                                        # Check password - TeamTalk stores passwords
                                        # in the format they were provided
                                        stored_password = str(acc.password)
                                        if stored_password == password:
                                            is_admin = True
                                    break
                            
                            if found:
                                response_queue.put({
                                    "success": True,
                                    "is_admin": is_admin
                                })
                            else:
                                response_queue.put({
                                    "success": True,
                                    "is_admin": False
                                })
                        except Exception as e:
                            response_queue.put({
                                "success": False,
                                "is_admin": False,
                                "error": str(e)
                            })
                    
                    elif action == "list_accounts":
                        try:
                            if instance is None:
                                response_queue.put({"accounts": [], "error": "Not connected"})
                                continue
                            accounts = await instance.list_user_accounts()
                            accounts_list = []
                            for acc in accounts:
                                accounts_list.append({
                                    "username": str(acc.username),
                                    "user_type": "admin" if acc.user_type == enums.UserType.ADMIN else "default",
                                    "note": str(acc.note) if hasattr(acc, 'note') else ""
                                })
                            response_queue.put({"accounts": accounts_list})
                        except Exception as e:
                            response_queue.put({"accounts": [], "error": str(e)})
                    
                    elif action == "get_online_users":
                        try:
                            if server is None:
                                response_queue.put({"users": [], "error": "Not connected"})
                                continue
                            users = server.get_users()
                            users_list = []
                            for user in users:
                                try:
                                    channel_name = ""
                                    if user.channel:
                                        channel_name = str(user.channel.name) if hasattr(user.channel, 'name') else ""
                                    users_list.append({
                                        "id": user.id,
                                        "username": str(user.username) if hasattr(user, 'username') else "",
                                        "nickname": str(user.nickname) if hasattr(user, 'nickname') else "",
                                        "channel": channel_name,
                                        "status": str(user.status_msg) if hasattr(user, 'status_msg') else ""
                                    })
                                except Exception:
                                    continue
                            response_queue.put({"users": users_list})
                        except Exception as e:
                            response_queue.put({"users": [], "error": str(e)})
                    
                    elif action == "send_private_message":
                        user_id = request.get("user_id")
                        message = request.get("message")
                        try:
                            if instance is None:
                                response_queue.put({"success": False, "error": "Not connected"})
                                continue
                            user = instance.get_user(user_id)
                            if user is None:
                                response_queue.put({"success": False, "error": "User not found"})
                                continue
                            # send_message is an async coroutine
                            result = user.send_message(message)
                            if result is not None:
                                await result
                            response_queue.put({"success": True})
                        except Exception as e:
                            response_queue.put({"success": False, "error": str(e)})
                    
                    elif action == "send_channel_message":
                        message = request.get("message")
                        try:
                            if instance is None:
                                response_queue.put({"success": False, "error": "Not connected"})
                                continue
                            # Get the current channel the bot is in
                            channel_id = instance.getMyChannelID()
                            if channel_id == 0:
                                response_queue.put({"success": False, "error": "Bot is not in a channel"})
                                continue
                            channel = instance.get_channel(channel_id)
                            if channel is None:
                                response_queue.put({"success": False, "error": "Channel not found"})
                                continue
                            # send_message is an async coroutine
                            result = channel.send_message(message)
                            if result is not None:
                                await result
                            response_queue.put({"success": True})
                        except Exception as e:
                            response_queue.put({"success": False, "error": str(e)})
                    
                    elif action == "get_channel_messages":
                        response_queue.put({"messages": list(channel_messages)})
                    
                    elif action == "clear_channel_messages":
                        channel_messages.clear()
                        response_queue.put({"success": True})
                    
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
    async def on_message(msg: tt_message.Message) -> None:
        """Handle incoming messages and store channel messages."""
        # Only store channel messages, not direct or broadcast
        if isinstance(msg, tt_message.ChannelMessage):
            try:
                channel_name = ""
                if hasattr(msg, 'channel') and msg.channel:
                    channel_name = str(msg.channel.name) if hasattr(msg.channel, 'name') else ""
                
                username = ""
                if hasattr(msg, 'user') and msg.user:
                    username = str(msg.user.nickname) if hasattr(msg.user, 'nickname') else str(msg.user.username) if hasattr(msg.user, 'username') else ""
                
                channel_messages.append({
                    "from_user": username,
                    "channel": channel_name,
                    "content": str(msg.content),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception:
                pass

    @bot.event
    async def on_error(ename: str, *args: Any, **kwargs: Any) -> None:
        response_queue.put({"error": f"TeamTalk error in {ename}: {args}"})

    bot.run()
