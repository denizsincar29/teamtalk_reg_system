"""Task scheduler for scheduled messages and channel operations.

This module provides a simple file-based task scheduler for:
- Scheduled broadcast messages
- Scheduled channel messages (bot joins channel first, then sends)
- Scheduled channel creation
- Recurring tasks (e.g., every N minutes)
- On user login tasks (trigger when user comes online)
- PM to online users (only sends if user is online)
- PM queue for offline users (delivers when they come online)
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

# Task storage file
TASKS_FILE = Path(__file__).parent.parent / "data" / "scheduled_tasks.json"

# Offline PM queue file
OFFLINE_PM_FILE = Path(__file__).parent.parent / "data" / "offline_pm_queue.json"


class TaskType:
    """Task type constants."""
    BROADCAST = "broadcast"
    CHANNEL_MESSAGE = "channel_message"
    CREATE_CHANNEL = "create_channel"
    PM_ONLINE = "pm_online"  # Send PM only if user is online
    ON_USER_LOGIN = "on_user_login"  # Trigger on user login (0-X seconds delay)
    STATUS_CHANGE = "status_change"  # Change bot status message


class TaskScheduler:
    """Manages scheduled tasks with file-based persistence."""
    
    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
        self.offline_pm_queue: dict[str, list[dict[str, Any]]] = {}  # username -> list of pending PMs
        self._running = False
        self._task: asyncio.Task | None = None
        self._manager = None  # Will be set during initialization
    
    def set_manager(self, manager: Any) -> None:
        """Set the TeamTalk manager for executing tasks."""
        self._manager = manager
    
    async def load_tasks(self) -> None:
        """Load tasks from file."""
        try:
            # Ensure data directory exists
            await aiofiles.os.makedirs(TASKS_FILE.parent, exist_ok=True)
            
            if await aiofiles.os.path.exists(TASKS_FILE):
                async with aiofiles.open(TASKS_FILE, "r", encoding="utf-8") as f:
                    content = await f.read()
                    self.tasks = json.loads(content) if content.strip() else {}
            else:
                self.tasks = {}
        except Exception as e:
            print(f"Error loading tasks: {e}")
            self.tasks = {}
        
        # Also load offline PM queue
        await self.load_offline_pm_queue()
    
    async def load_offline_pm_queue(self) -> None:
        """Load offline PM queue from file."""
        try:
            if await aiofiles.os.path.exists(OFFLINE_PM_FILE):
                async with aiofiles.open(OFFLINE_PM_FILE, "r", encoding="utf-8") as f:
                    content = await f.read()
                    self.offline_pm_queue = json.loads(content) if content.strip() else {}
            else:
                self.offline_pm_queue = {}
        except Exception as e:
            print(f"Error loading offline PM queue: {e}")
            self.offline_pm_queue = {}
    
    async def save_offline_pm_queue(self) -> None:
        """Save offline PM queue to file."""
        try:
            await aiofiles.os.makedirs(OFFLINE_PM_FILE.parent, exist_ok=True)
            async with aiofiles.open(OFFLINE_PM_FILE, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.offline_pm_queue, indent=2, default=str))
        except Exception as e:
            print(f"Error saving offline PM queue: {e}")
    
    async def save_tasks(self) -> None:
        """Save tasks to file."""
        try:
            # Ensure data directory exists
            await aiofiles.os.makedirs(TASKS_FILE.parent, exist_ok=True)
            
            async with aiofiles.open(TASKS_FILE, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.tasks, indent=2, default=str))
        except Exception as e:
            print(f"Error saving tasks: {e}")
    
    async def add_task(
        self,
        task_type: str,
        name: str,
        message: str = "",
        channel_id: int = 0,
        channel_name: str = "",
        channel_password: str = "",
        scheduled_time: datetime | None = None,
        recurring_minutes: int = 0,
        enabled: bool = True,
        target_username: str = "",
        delay_min_seconds: int = 0,
        delay_max_seconds: int = 0,
        status_mode: int = 0
    ) -> str:
        """Add a new scheduled task.
        
        Args:
            task_type: Type of task (broadcast, channel_message, create_channel, pm_online, on_user_login, status_change)
            name: Display name for the task
            message: Message content (for broadcast/channel_message/pm/status)
            channel_id: Target channel ID (for channel_message)
            channel_name: Channel name (for create_channel)
            channel_password: Channel password (for create_channel)
            scheduled_time: When to execute (None for recurring-only tasks or event-based)
            recurring_minutes: Repeat every N minutes (0 for one-time)
            enabled: Whether the task is active
            target_username: Target username (for pm_online, on_user_login)
            delay_min_seconds: Minimum delay in seconds (for on_user_login)
            delay_max_seconds: Maximum delay in seconds (for on_user_login)
            status_mode: Status mode for status_change (0=online, 1=away, 2=question)
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = {
            "id": task_id,
            "type": task_type,
            "name": name,
            "message": message,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "channel_password": channel_password,
            "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
            "target_username": target_username,
            "delay_min_seconds": delay_min_seconds,
            "delay_max_seconds": delay_max_seconds,
            "status_mode": status_mode,
            "recurring_minutes": recurring_minutes,
            "enabled": enabled,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "next_run": None
        }
        
        # Calculate next run time
        if scheduled_time:
            task["next_run"] = scheduled_time.isoformat()
        elif recurring_minutes > 0:
            task["next_run"] = (datetime.now() + timedelta(minutes=recurring_minutes)).isoformat()
        
        self.tasks[task_id] = task
        await self.save_tasks()
        return task_id
    
    async def update_task(self, task_id: str, **updates: Any) -> bool:
        """Update an existing task."""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        for key, value in updates.items():
            if key in task:
                if key == "scheduled_time":
                    # Handle datetime conversion and None/empty values
                    if isinstance(value, datetime):
                        task[key] = value.isoformat()
                    elif value is None or value == "":
                        task[key] = None
                    else:
                        task[key] = value
                else:
                    task[key] = value
        
        # Recalculate next run if schedule changed
        if "scheduled_time" in updates or "recurring_minutes" in updates:
            recurring = task.get("recurring_minutes", 0)
            scheduled = task.get("scheduled_time")
            
            if scheduled:
                # Has a specific scheduled time
                task["next_run"] = scheduled
            elif recurring > 0:
                # Recurring task without specific start time
                task["next_run"] = (datetime.now() + timedelta(minutes=recurring)).isoformat()
            else:
                # No schedule set
                task["next_run"] = None
        
        await self.save_tasks()
        return True
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id not in self.tasks:
            return False
        
        del self.tasks[task_id]
        await self.save_tasks()
        return True
    
    async def get_tasks(self) -> list[dict[str, Any]]:
        """Get all tasks."""
        return list(self.tasks.values())
    
    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Get a specific task."""
        return self.tasks.get(task_id)
    
    async def toggle_task(self, task_id: str) -> bool:
        """Toggle a task's enabled state."""
        if task_id not in self.tasks:
            return False
        
        self.tasks[task_id]["enabled"] = not self.tasks[task_id]["enabled"]
        await self.save_tasks()
        return True
    
    async def execute_task(self, task: dict[str, Any]) -> tuple[bool, str | None]:
        """Execute a single task.
        
        Returns:
            Tuple of (success, error_message)
        """
        if not self._manager:
            return False, "Manager not initialized"
        
        task_type = task.get("type")
        
        try:
            if task_type == TaskType.BROADCAST:
                message = task.get("message", "")
                if message:
                    success, error = await self._manager.send_broadcast_message(message)
                    return success, error
                return False, "No message specified"
            
            elif task_type == TaskType.CHANNEL_MESSAGE:
                channel_id = task.get("channel_id", 0)
                message = task.get("message", "")
                
                if not message:
                    return False, "No message specified"
                
                if channel_id > 0:
                    # First join the channel
                    current_channel = await self._manager.get_current_channel()
                    if current_channel != channel_id:
                        success, error = await self._manager.join_channel(channel_id)
                        if not success:
                            return False, f"Failed to join channel: {error}"
                        # Wait a bit for channel join to complete
                        await asyncio.sleep(0.5)
                
                # Send the message
                success, error = await self._manager.send_channel_message(message)
                return success, error
            
            elif task_type == TaskType.CREATE_CHANNEL:
                # Channel creation would require additional SDK support
                # For now, return not implemented
                return False, "Channel creation not yet implemented"
            
            elif task_type == TaskType.PM_ONLINE:
                # Send PM only if user is online
                target_username = task.get("target_username", "")
                message = task.get("message", "")
                
                if not target_username:
                    return False, "No target username specified"
                if not message:
                    return False, "No message specified"
                
                # Get online users and find target
                users, error = await self._manager.get_online_users()
                if error:
                    return False, f"Failed to get online users: {error}"
                
                user_id = None
                for user in users:
                    if user.get("username", "").lower() == target_username.lower():
                        user_id = user.get("id")
                        break
                
                if user_id is None:
                    return True, "User not online, skipping"  # Success but skipped
                
                success, error = await self._manager.send_private_message(user_id, message)
                return success, error
            
            elif task_type == TaskType.STATUS_CHANGE:
                # Change bot status message
                status_mode = task.get("status_mode", 0)
                status_message = task.get("message", "")
                
                success, error = await self._manager.change_status(status_mode, status_message)
                return success, error
            
            return False, f"Unknown task type: {task_type}"
            
        except Exception as e:
            return False, str(e)
    
    async def queue_offline_pm(self, username: str, message: str, task_name: str = "") -> None:
        """Queue a PM for an offline user."""
        username_lower = username.lower()
        if username_lower not in self.offline_pm_queue:
            self.offline_pm_queue[username_lower] = []
        
        self.offline_pm_queue[username_lower].append({
            "message": message,
            "task_name": task_name,
            "queued_at": datetime.now().isoformat()
        })
        await self.save_offline_pm_queue()
    
    async def deliver_offline_pms(self, username: str, user_id: int) -> int:
        """Deliver queued PMs to a user who just came online.
        
        Returns:
            Number of messages delivered
        """
        if not self._manager:
            return 0
        
        username_lower = username.lower()
        if username_lower not in self.offline_pm_queue:
            return 0
        
        messages = self.offline_pm_queue.pop(username_lower, [])
        delivered = 0
        
        for pm in messages:
            try:
                success, _ = await self._manager.send_private_message(user_id, pm["message"])
                if success:
                    delivered += 1
            except Exception as e:
                print(f"Failed to deliver offline PM: {e}")
        
        await self.save_offline_pm_queue()
        return delivered
    
    async def handle_user_login(self, username: str, user_id: int) -> None:
        """Handle user login event - trigger on_user_login tasks and deliver offline PMs."""
        if not self._manager:
            return
        
        # First, deliver any queued offline PMs
        delivered = await self.deliver_offline_pms(username, user_id)
        if delivered > 0:
            print(f"Delivered {delivered} offline PM(s) to {username}")
        
        # Then, trigger on_user_login tasks
        for task_id, task in list(self.tasks.items()):
            if not task.get("enabled", True):
                continue
            
            if task.get("type") != TaskType.ON_USER_LOGIN:
                continue
            
            target = task.get("target_username", "")
            # Empty target means any user, otherwise match specific user
            if target and target.lower() != username.lower():
                continue
            
            # Calculate delay
            min_delay = task.get("delay_min_seconds", 0)
            max_delay = task.get("delay_max_seconds", 0)
            
            if max_delay > min_delay:
                delay = random.randint(min_delay, max_delay)
            else:
                delay = min_delay
            
            # Schedule the task execution with delay
            asyncio.create_task(self._execute_login_task_delayed(task, user_id, delay))
    
    async def _execute_login_task_delayed(self, task: dict[str, Any], user_id: int, delay: int) -> None:
        """Execute a login-triggered task after a delay."""
        if delay > 0:
            await asyncio.sleep(delay)
        
        task_type = task.get("type")
        message = task.get("message", "")
        
        if not message:
            print(f"Login task {task.get('name', 'unnamed')} has no message")
            return
        
        try:
            # For on_user_login tasks, send a PM to the user who logged in
            success, error = await self._manager.send_private_message(user_id, message)
            if success:
                print(f"Sent login message to user {user_id}: {message[:50]}...")
            else:
                print(f"Failed to send login message: {error}")
        except Exception as e:
            print(f"Error executing login task: {e}")
    
    async def get_offline_pm_queue(self) -> dict[str, list[dict[str, Any]]]:
        """Get the current offline PM queue."""
        return self.offline_pm_queue.copy()
    
    async def clear_offline_pm_queue(self, username: str) -> bool:
        """Clear queued PMs for a specific user."""
        username_lower = username.lower()
        if username_lower in self.offline_pm_queue:
            del self.offline_pm_queue[username_lower]
            await self.save_offline_pm_queue()
            return True
        return False
    
    async def _run_scheduler(self) -> None:
        """Background task that checks and executes scheduled tasks."""
        while self._running:
            try:
                now = datetime.now()
                
                for task_id, task in list(self.tasks.items()):
                    if not task.get("enabled", True):
                        continue
                    
                    next_run_str = task.get("next_run")
                    if not next_run_str:
                        continue
                    
                    next_run = datetime.fromisoformat(next_run_str)
                    
                    if now >= next_run:
                        # Execute the task
                        print(f"Executing scheduled task: {task.get('name', task_id)}")
                        success, error = await self.execute_task(task)
                        
                        if not success:
                            print(f"Task execution failed: {error}")
                        
                        # Update last run time
                        task["last_run"] = now.isoformat()
                        
                        # Calculate next run for recurring tasks
                        recurring_minutes = task.get("recurring_minutes", 0)
                        if recurring_minutes > 0:
                            task["next_run"] = (now + timedelta(minutes=recurring_minutes)).isoformat()
                        else:
                            # One-time task completed, disable it
                            task["enabled"] = False
                            task["next_run"] = None
                        
                        await self.save_tasks()
                
            except Exception as e:
                print(f"Scheduler error: {e}")
            
            # Check every 30 seconds
            await asyncio.sleep(30)
    
    async def start(self) -> None:
        """Start the scheduler background task."""
        if self._running:
            return
        
        await self.load_tasks()
        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


# Global scheduler instance
task_scheduler = TaskScheduler()
