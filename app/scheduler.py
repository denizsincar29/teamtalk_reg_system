"""Task scheduler for scheduled messages and channel operations.

This module provides a simple file-based task scheduler for:
- Scheduled broadcast messages
- Scheduled channel messages (bot joins channel first, then sends)
- Scheduled channel creation
- Recurring tasks (e.g., every N minutes)
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

# Task storage file
TASKS_FILE = Path(__file__).parent.parent / "data" / "scheduled_tasks.json"


class TaskType:
    """Task type constants."""
    BROADCAST = "broadcast"
    CHANNEL_MESSAGE = "channel_message"
    CREATE_CHANNEL = "create_channel"


class TaskScheduler:
    """Manages scheduled tasks with file-based persistence."""
    
    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
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
        enabled: bool = True
    ) -> str:
        """Add a new scheduled task.
        
        Args:
            task_type: Type of task (broadcast, channel_message, create_channel)
            name: Display name for the task
            message: Message content (for broadcast/channel_message)
            channel_id: Target channel ID (for channel_message)
            channel_name: Channel name (for create_channel)
            channel_password: Channel password (for create_channel)
            scheduled_time: When to execute (None for recurring-only tasks)
            recurring_minutes: Repeat every N minutes (0 for one-time)
            enabled: Whether the task is active
            
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
            
            return False, f"Unknown task type: {task_type}"
            
        except Exception as e:
            return False, str(e)
    
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
