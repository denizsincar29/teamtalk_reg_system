"""TeamTalk bot worker that runs in a separate process."""

import asyncio
import logging
import sys
from collections import deque
from datetime import datetime
from multiprocessing import Queue
from typing import Any

import pytalk
from pytalk import enums, Permission, message as tt_message
from pytalk import channel as tt_channel
from pytalk import user as tt_user
from pytalk.enums import Status

from .config import BOT_SERVER_CONFIG

# Set up logging for the worker process
# Note: This runs in a separate process, so we set up logging here directly
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
worker_logger = logging.getLogger("teamtalk.bot_worker")

# Status mode bitmask for extracting mode from combined status integer
STATUS_MODE_MASK = 0xFF

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

# Maximum number of events to store
MAX_EVENTS = 100


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
    # Store events in a deque with max size
    events: deque[dict[str, Any]] = deque(maxlen=MAX_EVENTS)

    def _reply(request: dict, payload: dict) -> None:
        """Send a response that carries back the request's correlation ID."""
        payload["request_id"] = request.get("request_id")
        response_queue.put(payload)

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
                                _reply(request, {"exists": False, "error": "Not connected"})
                                continue
                            accounts = await instance.list_user_accounts()
                            exists = any(
                                str(acc.username).lower() == username.lower()
                                for acc in accounts
                            )
                            _reply(request, {"exists": exists})
                        except Exception as e:
                            _reply(request, {"exists": False, "error": str(e)})
                    
                    elif action == "create_user":
                        username = request.get("username")
                        password = request.get("password")
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
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
                            _reply(request, {"success": True})
                        except Exception as e:
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "broadcast":
                        message = request.get("message")
                        try:
                            if server is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            server.send_message(message)
                            _reply(request, {"success": True})
                        except Exception as e:
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "authenticate_admin":
                        username = request.get("username")
                        password = request.get("password")
                        try:
                            if instance is None:
                                _reply(request, {
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
                                _reply(request, {
                                    "success": True,
                                    "is_admin": is_admin
                                })
                            else:
                                _reply(request, {
                                    "success": True,
                                    "is_admin": False
                                })
                        except Exception as e:
                            _reply(request, {
                                "success": False,
                                "is_admin": False,
                                "error": str(e)
                            })
                    
                    elif action == "list_accounts":
                        try:
                            if instance is None:
                                _reply(request, {"accounts": [], "error": "Not connected"})
                                continue
                            accounts = await instance.list_user_accounts()
                            accounts_list = []
                            for acc in accounts:
                                accounts_list.append({
                                    "username": str(acc.username),
                                    "user_type": "admin" if acc.user_type == enums.UserType.ADMIN else "default",
                                    "note": str(acc.note) if hasattr(acc, 'note') else ""
                                })
                            _reply(request, {"accounts": accounts_list})
                        except Exception as e:
                            _reply(request, {"accounts": [], "error": str(e)})
                    
                    elif action == "get_online_users":
                        try:
                            if server is None:
                                _reply(request, {"users": [], "error": "Not connected"})
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
                            _reply(request, {"users": users_list})
                        except Exception as e:
                            _reply(request, {"users": [], "error": str(e)})
                    
                    elif action == "send_private_message":
                        user_id = request.get("user_id")
                        message = request.get("message")
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            user = instance.get_user(user_id)
                            if user is None:
                                _reply(request, {"success": False, "error": "User not found"})
                                continue
                            # send_message is an async coroutine
                            result = user.send_message(message)
                            if result is not None:
                                await result
                            _reply(request, {"success": True})
                        except Exception as e:
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "send_channel_message":
                        message = request.get("message")
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            # Get the current channel the bot is in
                            channel_id = instance.getMyChannelID()
                            if channel_id == 0:
                                _reply(request, {"success": False, "error": "Bot is not in a channel"})
                                continue
                            channel = instance.get_channel(channel_id)
                            if channel is None:
                                _reply(request, {"success": False, "error": "Channel not found"})
                                continue
                            # send_message is an async coroutine
                            result = channel.send_message(message)
                            if result is not None:
                                await result
                            _reply(request, {"success": True})
                        except Exception as e:
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "get_channel_messages":
                        _reply(request, {"messages": list(channel_messages)})
                    
                    elif action == "clear_channel_messages":
                        channel_messages.clear()
                        _reply(request, {"success": True})
                    
                    elif action == "send_broadcast_message":
                        message = request.get("message")
                        try:
                            if server is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            server.send_message(message)
                            _reply(request, {"success": True})
                        except Exception as e:
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "get_channels":
                        try:
                            if server is None:
                                _reply(request, {"channels": [], "error": "Not connected"})
                                continue
                            channels = server.get_channels()
                            channels_list = []
                            for ch in channels:
                                try:
                                    has_password = bool(ch._channel.bPassword) if hasattr(ch._channel, 'bPassword') else False
                                    parent_id = ch._channel.nParentID if hasattr(ch._channel, 'nParentID') else 0
                                    channels_list.append({
                                        "id": ch.id,
                                        "name": str(ch.name) if hasattr(ch, 'name') else "",
                                        "path": str(ch.path) if hasattr(ch, 'path') else "",
                                        "has_password": has_password,
                                        "parent_id": parent_id,
                                        "max_users": ch.max_users if hasattr(ch, 'max_users') else 0
                                    })
                                except Exception:
                                    continue
                            _reply(request, {"channels": channels_list})
                        except Exception as e:
                            _reply(request, {"channels": [], "error": str(e)})
                    
                    elif action == "join_channel":
                        channel_id = request.get("channel_id")
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            # Get channel info to find password (admin can see passwords)
                            channel = instance.get_channel(channel_id)
                            if channel is None:
                                _reply(request, {"success": False, "error": "Channel not found"})
                                continue
                            # Get the channel password from the SDK channel object
                            # Admin accounts can access szPassword field
                            password = ""
                            try:
                                if hasattr(channel, '_channel') and hasattr(channel._channel, 'szPassword'):
                                    from pytalk.implementation.TeamTalkPy import TeamTalk5 as sdk
                                    password = sdk.ttstr(channel._channel.szPassword)
                            except Exception:
                                password = ""
                            instance.join_channel_by_id(channel_id, password)
                            _reply(request, {"success": True})
                        except Exception as e:
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "leave_channel":
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            # Get current channel to find its parent
                            current_channel_id = instance.getMyChannelID()
                            if current_channel_id == 0:
                                _reply(request, {"success": False, "error": "Not in any channel"})
                                continue
                            
                            current_channel = instance.get_channel(current_channel_id)
                            parent_id = 0
                            if current_channel and hasattr(current_channel, '_channel'):
                                parent_id = current_channel._channel.nParentID if hasattr(current_channel._channel, 'nParentID') else 0
                            
                            if parent_id > 0:
                                # Join parent channel instead of leaving to vacuum
                                parent_channel = instance.get_channel(parent_id)
                                password = ""
                                try:
                                    if parent_channel and hasattr(parent_channel, '_channel') and hasattr(parent_channel._channel, 'szPassword'):
                                        from pytalk.implementation.TeamTalkPy import TeamTalk5 as sdk
                                        password = sdk.ttstr(parent_channel._channel.szPassword)
                                except Exception:
                                    password = ""
                                instance.join_channel_by_id(parent_id, password)
                            else:
                                # No parent (root channel) - leave to vacuum
                                instance.leave_channel()
                            _reply(request, {"success": True})
                        except Exception as e:
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "get_current_channel":
                        try:
                            if instance is None:
                                _reply(request, {"channel_id": 0, "error": "Not connected"})
                                continue
                            channel_id = instance.getMyChannelID()
                            _reply(request, {"channel_id": channel_id})
                        except Exception as e:
                            _reply(request, {"channel_id": 0, "error": str(e)})
                    
                    elif action == "get_events":
                        _reply(request, {"events": list(events)})
                    
                    elif action == "clear_events":
                        events.clear()
                        _reply(request, {"success": True})
                    
                    elif action == "kick_user":
                        user_id = request.get("user_id")
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            # Kick the user from the server
                            instance.kick_user(user_id, 0)  # 0 = from server
                            _reply(request, {"success": True})
                        except Exception as e:
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "ban_user":
                        user_id = request.get("user_id")
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            # Ban the user from the server
                            instance.ban_user(user_id)
                            _reply(request, {"success": True})
                        except Exception as e:
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "ban_username":
                        username = request.get("username")
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            # Ban a username (for offline users)
                            # Check if the method exists before calling
                            if not hasattr(instance, 'ban_user_account'):
                                worker_logger.error("ban_user_account method not available in TeamTalk SDK")
                                _reply(request, {"success": False, "error": "Ban by username not supported by TeamTalk SDK"})
                                continue
                            instance.ban_user_account(username)
                            worker_logger.info(f"Banned user account: {username}")
                            _reply(request, {"success": True})
                        except Exception as e:
                            worker_logger.error(f"Failed to ban username {username}: {e}", exc_info=True)
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "change_status":
                        status_mode = int(request.get("status_mode", 0))  # 0 = online
                        status_message = str(request.get("status_message", ""))
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            # Use pytalk Status enum for proper status flags
                            # status_mode: 0=online, 1=away, 2=question
                            # Note: Status.online, .away, .question are classmethods that return _StatusBuilder
                            if status_mode == 1:
                                status_flags = Status.away().neutral
                            elif status_mode == 2:
                                status_flags = Status.question().neutral
                            else:
                                status_flags = Status.online().neutral
                            instance.change_status(status_flags, status_message)
                            worker_logger.info(f"Changed status to mode={status_mode}, message='{status_message}'")
                            _reply(request, {"success": True})
                        except Exception as e:
                            worker_logger.error(f"Failed to change status: {e}", exc_info=True)
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "get_status":
                        try:
                            if instance is None:
                                _reply(request, {"status_mode": 0, "status_message": "", "error": "Not connected"})
                                continue
                            user_id = instance.getMyUserID()
                            user = instance.get_user(user_id)
                            status_mode = getattr(user, 'status_mode', 0) if user else 0
                            status_message = str(getattr(user, 'status_msg', '')) if user else ""
                            # Extract mode bits (0=online, 1=away, 2=question)
                            mode_bits = status_mode & STATUS_MODE_MASK
                            _reply(request, {"status_mode": mode_bits, "status_message": status_message})
                        except Exception as e:
                            worker_logger.error(f"Failed to get status: {e}", exc_info=True)
                            _reply(request, {"status_mode": 0, "status_message": "", "error": str(e)})
                    
                    elif action == "stream_audio":
                        file_path = request.get("file_path")
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            # Check if bot is in a channel
                            channel_id = instance.getMyChannelID()
                            if channel_id == 0:
                                _reply(request, {"success": False, "error": "Bot is not in a channel"})
                                continue
                            channel = instance.get_channel(channel_id)
                            if channel is None:
                                _reply(request, {"success": False, "error": "Channel not found"})
                                continue
                            # Import and use the Streamer class
                            from pytalk.streamer import Streamer
                            streamer = Streamer.get_streamer_for_channel(channel)
                            streamer.stream(file_path)
                            worker_logger.info(f"Started streaming audio file: {file_path}")
                            _reply(request, {"success": True})
                        except Exception as e:
                            worker_logger.error(f"Failed to stream audio: {e}", exc_info=True)
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "stop_audio":
                        try:
                            if instance is None:
                                _reply(request, {"success": False, "error": "Not connected"})
                                continue
                            channel_id = instance.getMyChannelID()
                            if channel_id == 0:
                                _reply(request, {"success": False, "error": "Bot is not in a channel"})
                                continue
                            channel = instance.get_channel(channel_id)
                            if channel is None:
                                _reply(request, {"success": False, "error": "Channel not found"})
                                continue
                            # Get and stop the streamer for this channel
                            from pytalk.streamer import Streamer
                            streamer = Streamer.get_streamer_for_channel(channel)
                            streamer.stop()
                            worker_logger.info("Stopped audio streaming")
                            _reply(request, {"success": True})
                        except Exception as e:
                            worker_logger.error(f"Failed to stop audio: {e}", exc_info=True)
                            _reply(request, {"success": False, "error": str(e)})
                    
                    elif action == "shutdown":
                        worker_logger.info("Shutting down bot worker")
                        break
            except Exception as e:
                worker_logger.error(f"Error processing request: {e}", exc_info=True)

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
        
        # Check if bot is an admin - exit with error if not
        if not srv.teamtalk_instance.is_admin():
            import sys
            print("ERROR: Bot account does not have admin privileges on TeamTalk server.", file=sys.stderr)
            print("The bot must be logged in with an admin account to function properly.", file=sys.stderr)
            print("Please configure the bot with admin credentials.", file=sys.stderr)
            worker_logger.error("Bot account is not an admin on TeamTalk server.")
            sys.exit(1)
        
        instance_holder["ready"] = True
        
        # Add event for bot login
        events.append({
            "type": "bot_connected",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    @bot.event
    async def on_user_login(user: tt_user.User) -> None:
        """Handle user login to server."""
        try:
            username = str(user.username) if hasattr(user, 'username') else ""
            nickname = str(user.nickname) if hasattr(user, 'nickname') else username
            user_id = user.id if hasattr(user, 'id') else 0
            events.append({
                "type": "user_login",
                "username": username,
                "nickname": nickname,
                "user_id": user_id,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            # Deliver queued offline PMs and trigger on_user_login tasks
            if username and user_id:
                from .scheduler import task_scheduler
                await task_scheduler.handle_user_login(username, user_id)
        except Exception:
            pass

    @bot.event
    async def on_user_logout(user: tt_user.User) -> None:
        """Handle user logout from server."""
        try:
            username = str(user.username) if hasattr(user, 'username') else ""
            nickname = str(user.nickname) if hasattr(user, 'nickname') else username
            events.append({
                "type": "user_logout",
                "username": username,
                "nickname": nickname,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception:
            pass

    @bot.event
    async def on_user_join(user: tt_user.User, channel: tt_channel.Channel) -> None:
        """Handle user joining a channel."""
        try:
            username = str(user.username) if hasattr(user, 'username') else ""
            nickname = str(user.nickname) if hasattr(user, 'nickname') else username
            channel_name = str(channel.name) if hasattr(channel, 'name') else ""
            # Root channel may have empty name, "/" or other indicators
            if not channel_name or channel_name == "/" or channel_name.strip() == "":
                channel_name = ""  # Will be replaced with "root" in frontend
            events.append({
                "type": "user_join_channel",
                "username": username,
                "nickname": nickname,
                "channel": channel_name,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception:
            pass

    @bot.event
    async def on_user_left(user: tt_user.User, channel: tt_channel.Channel) -> None:
        """Handle user leaving a channel."""
        try:
            username = str(user.username) if hasattr(user, 'username') else ""
            nickname = str(user.nickname) if hasattr(user, 'nickname') else username
            channel_name = str(channel.name) if hasattr(channel, 'name') else ""
            # Root channel may have empty name, "/" or other indicators
            if not channel_name or channel_name == "/" or channel_name.strip() == "":
                channel_name = ""  # Will be replaced with "root" in frontend
            events.append({
                "type": "user_left_channel",
                "username": username,
                "nickname": nickname,
                "channel": channel_name,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception:
            pass

    @bot.event
    async def on_channel_new(channel: tt_channel.Channel) -> None:
        """Handle new channel creation."""
        try:
            channel_name = str(channel.name) if hasattr(channel, 'name') else ""
            events.append({
                "type": "channel_new",
                "channel": channel_name,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception:
            pass

    @bot.event
    async def on_channel_delete(channel: tt_channel.Channel) -> None:
        """Handle channel deletion."""
        try:
            channel_name = str(channel.name) if hasattr(channel, 'name') else ""
            events.append({
                "type": "channel_delete",
                "channel": channel_name,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception:
            pass

    @bot.event
    async def on_my_connection_lost(instance: Any) -> None:
        """Handle connection lost."""
        try:
            # Mark as not ready so process_requests stops accepting requests
            # against the now-dead connection.
            instance_holder["ready"] = False
            instance_holder["instance"] = None
            instance_holder["server"] = None
            events.append({
                "type": "connection_lost",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception:
            pass

    @bot.event
    async def on_message(msg: tt_message.Message) -> None:
        """Handle incoming messages and store channel and direct messages."""
        try:
            # Get sender info
            username = ""
            if hasattr(msg, 'user') and msg.user:
                username = str(msg.user.nickname) if hasattr(msg.user, 'nickname') else str(msg.user.username) if hasattr(msg.user, 'username') else ""
            
            if isinstance(msg, tt_message.ChannelMessage):
                channel_name = ""
                if hasattr(msg, 'channel') and msg.channel:
                    channel_name = str(msg.channel.name) if hasattr(msg.channel, 'name') else ""
                
                channel_messages.append({
                    "type": "channel",
                    "from_user": username,
                    "channel": channel_name,
                    "content": str(msg.content),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            elif isinstance(msg, tt_message.DirectMessage):
                # Store private/direct messages too
                channel_messages.append({
                    "type": "private",
                    "from_user": username,
                    "channel": "",
                    "content": str(msg.content),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            elif isinstance(msg, tt_message.BroadcastMessage):
                # Store broadcast messages with distinct type
                channel_messages.append({
                    "type": "broadcast",
                    "from_user": username,
                    "channel": "",
                    "content": str(msg.content),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        except Exception:
            pass

    @bot.event
    async def on_error(ename: str, *args: Any, **kwargs: Any) -> None:
        # Log only – do NOT push to response_queue here because there is no
        # correlated request in flight. An orphan response would be consumed
        # by the next unrelated caller and corrupt its result.
        worker_logger.error("TeamTalk error in %s: %s", ename, args)

    bot.run()
