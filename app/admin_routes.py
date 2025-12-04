"""Admin panel routes for the TeamTalk Registration System."""

import asyncio
import html
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from .i18n import DEFAULT_LANGUAGE, LANGUAGES, get_translations
from .manager import tt_manager
from .scheduler import task_scheduler, TaskType

router = APIRouter(prefix="/admin")

# Set up templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Simple session storage (in-memory, suitable for single-process deployment)
# Note: Sessions will be lost when the application restarts. For production 
# deployments requiring session persistence across restarts, consider using
# a persistent storage solution (e.g., Redis, database).
# Format: {session_token: {"username": str, "expires": datetime}}
admin_sessions: dict[str, dict[str, Any]] = {}

# Session expiry time - 30 days for PWA persistence
SESSION_EXPIRY_DAYS = 30
SESSION_EXPIRY_SECONDS = SESSION_EXPIRY_DAYS * 24 * 3600


def get_lang(lang: str | None) -> str:
    """Get valid language code."""
    if lang and lang in LANGUAGES:
        return lang
    return DEFAULT_LANGUAGE


def create_session(username: str) -> str:
    """Create a new admin session and return the token."""
    token = secrets.token_urlsafe(32)
    admin_sessions[token] = {
        "username": username,
        "expires": datetime.now() + timedelta(days=SESSION_EXPIRY_DAYS)
    }
    return token


def validate_session(token: str | None) -> str | None:
    """Validate session token and return username if valid.
    
    Also refreshes the session expiry time to extend the session.
    """
    if not token:
        return None
    session = admin_sessions.get(token)
    if not session:
        return None
    if datetime.now() > session["expires"]:
        del admin_sessions[token]
        return None
    # Refresh the session expiry (sliding expiration)
    session["expires"] = datetime.now() + timedelta(days=SESSION_EXPIRY_DAYS)
    return session["username"]


def destroy_session(token: str) -> None:
    """Destroy a session."""
    if token in admin_sessions:
        del admin_sessions[token]


def get_session_token(request: Request) -> str | None:
    """Get session token from cookies."""
    return request.cookies.get("admin_session")


@router.get("/", response_class=HTMLResponse)
async def admin_home(request: Request, lang: str = Query(default=None)) -> HTMLResponse:
    """Render the admin login page or dashboard."""
    lang = get_lang(lang)
    t = get_translations(lang)
    
    # Check if already logged in
    token = get_session_token(request)
    username = validate_session(token)
    
    if username:
        response = templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "lang": lang,
            "t": t,
            "username": html.escape(username)
        })
        # Refresh the cookie to extend its expiry (sliding expiration)
        response.set_cookie(
            key="admin_session",
            value=token,
            httponly=True,
            max_age=SESSION_EXPIRY_SECONDS,
            samesite="lax"
        )
        return response
    
    return templates.TemplateResponse("admin_login.html", {
        "request": request,
        "lang": lang,
        "t": t,
        "error": ""
    })


@router.post("/login", response_model=None)
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    lang: str = Query(default=None)
) -> HTMLResponse | RedirectResponse:
    """Handle admin login."""
    lang = get_lang(lang)
    t = get_translations(lang)
    
    # Clean input
    username = username.strip()
    password = password.strip()
    
    if not username or not password:
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "lang": lang,
            "t": t,
            "error": t.get("error_required", "Username and password are required.")
        })
    
    # Try to authenticate with the TeamTalk server
    success, is_admin, error = await tt_manager.authenticate_admin(username, password)
    
    if not success:
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "lang": lang,
            "t": t,
            "error": error or t.get("admin_connection_error", "Could not connect to the server.")
        })
    
    if not is_admin:
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "lang": lang,
            "t": t,
            "error": t.get("admin_login_error", "Invalid credentials or not an admin account.")
        })
    
    # Create session and redirect to dashboard
    token = create_session(username)
    response = RedirectResponse(
        url=str(request.url_for("admin_home")) + f"?lang={lang}",
        status_code=303
    )
    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
        max_age=SESSION_EXPIRY_SECONDS,
        samesite="lax"
    )
    return response


@router.get("/logout")
async def admin_logout(request: Request, lang: str = Query(default=None)) -> RedirectResponse:
    """Handle admin logout."""
    lang = get_lang(lang)
    token = get_session_token(request)
    if token:
        destroy_session(token)
    
    response = RedirectResponse(
        url=str(request.url_for("admin_home")) + f"?lang={lang}",
        status_code=303
    )
    response.delete_cookie(key="admin_session")
    return response


@router.get("/api/accounts")
async def get_accounts(request: Request) -> JSONResponse:
    """Get list of user accounts."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    accounts, error = await tt_manager.list_user_accounts()
    
    if error:
        return JSONResponse({"error": str(error)}, status_code=500)
    
    return JSONResponse({"accounts": accounts})


@router.get("/api/users")
async def get_online_users(request: Request) -> JSONResponse:
    """Get list of online users."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    users, error = await tt_manager.get_online_users()
    
    if error:
        return JSONResponse({"error": str(error)}, status_code=500)
    
    return JSONResponse({"users": users})


@router.post("/api/send_message")
async def send_private_message(
    request: Request,
    user_id: int = Form(...),
    message: str = Form(...)
) -> JSONResponse:
    """Send a private message to a user."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    message = message.strip()
    if not message:
        return JSONResponse({"error": "Message cannot be empty"}, status_code=400)
    
    success, error = await tt_manager.send_private_message(user_id, message)
    
    if not success:
        return JSONResponse({"error": str(error)}, status_code=500)
    
    return JSONResponse({"success": True})


@router.post("/api/send_channel_message")
async def send_channel_message(
    request: Request,
    message: str = Form(...)
) -> JSONResponse:
    """Send a message to the channel the bot is in."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    message = message.strip()
    if not message:
        return JSONResponse({"error": "Message cannot be empty"}, status_code=400)
    
    success, error = await tt_manager.send_channel_message(message)
    
    if not success:
        return JSONResponse({"error": str(error)}, status_code=500)
    
    return JSONResponse({"success": True})


@router.get("/api/messages")
async def get_channel_messages(request: Request) -> JSONResponse:
    """Get channel messages."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    messages = await tt_manager.get_channel_messages()
    
    return JSONResponse({"messages": messages})


@router.post("/api/messages/clear")
async def clear_channel_messages(request: Request) -> JSONResponse:
    """Clear channel messages."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    await tt_manager.clear_channel_messages()
    
    return JSONResponse({"success": True})


async def message_and_event_generator(request: Request) -> AsyncGenerator[str, None]:
    """Generate SSE events for message and event updates."""
    last_msg_count = 0
    last_messages: list[dict[str, Any]] = []
    last_event_count = 0
    last_events: list[dict[str, Any]] = []
    
    while True:
        # Check if client disconnected
        if await request.is_disconnected():
            break
        
        messages = await tt_manager.get_channel_messages()
        events = await tt_manager.get_events()
        
        # Check for new messages or events
        msgs_changed = len(messages) != last_msg_count or messages != last_messages
        events_changed = len(events) != last_event_count or events != last_events
        
        if msgs_changed or events_changed:
            # Send combined data
            yield f"data: {json.dumps({'messages': messages, 'events': events})}\n\n"
            last_msg_count = len(messages)
            last_messages = messages.copy() if messages else []
            last_event_count = len(events)
            last_events = events.copy() if events else []
        
        # Wait a bit before checking again (500ms for responsive updates)
        await asyncio.sleep(0.5)


@router.get("/api/messages/stream")
async def stream_messages(request: Request) -> StreamingResponse:
    """Stream messages and events using Server-Sent Events."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    return StreamingResponse(
        message_and_event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/api/events")
async def get_events(request: Request) -> JSONResponse:
    """Get server events."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    events = await tt_manager.get_events()
    
    return JSONResponse({"events": events})


@router.post("/api/events/clear")
async def clear_events(request: Request) -> JSONResponse:
    """Clear server events."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    await tt_manager.clear_events()
    
    return JSONResponse({"success": True})


@router.post("/api/broadcast")
async def send_broadcast_message(
    request: Request,
    message: str = Form(...)
) -> JSONResponse:
    """Send a broadcast message to all users on the server."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    message = message.strip()
    if not message:
        return JSONResponse({"error": "Message cannot be empty"}, status_code=400)
    
    success, error = await tt_manager.send_broadcast_message(message)
    
    if not success:
        return JSONResponse({"error": str(error)}, status_code=500)
    
    return JSONResponse({"success": True})


@router.get("/api/channels")
async def get_channels(request: Request) -> JSONResponse:
    """Get list of all channels on the server."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    channels = await tt_manager.get_channels()
    current_channel = await tt_manager.get_current_channel()
    
    return JSONResponse({"channels": channels, "current_channel": current_channel})


@router.post("/api/channels/join")
async def join_channel(
    request: Request,
    channel_id: int = Form(...)
) -> JSONResponse:
    """Make the bot join a channel."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    success, error = await tt_manager.join_channel(channel_id)
    
    if not success:
        return JSONResponse({"error": str(error)}, status_code=500)
    
    return JSONResponse({"success": True})


@router.post("/api/channels/leave")
async def leave_channel(request: Request) -> JSONResponse:
    """Make the bot leave its current channel."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    success, error = await tt_manager.leave_channel()
    
    if not success:
        return JSONResponse({"error": str(error)}, status_code=500)
    
    return JSONResponse({"success": True})


# Scheduler routes

@router.get("/api/tasks")
async def get_tasks(request: Request) -> JSONResponse:
    """Get all scheduled tasks."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    tasks = await task_scheduler.get_tasks()
    return JSONResponse({"tasks": tasks})


@router.post("/api/tasks")
async def create_task(
    request: Request,
    task_type: str = Form(...),
    name: str = Form(...),
    message: str = Form(""),
    channel_id: int = Form(0),
    scheduled_time: str = Form(""),
    recurring_minutes: int = Form(0)
) -> JSONResponse:
    """Create a new scheduled task."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Validate task type
    if task_type not in [TaskType.BROADCAST, TaskType.CHANNEL_MESSAGE, TaskType.CREATE_CHANNEL]:
        return JSONResponse({"error": "Invalid task type"}, status_code=400)
    
    # Parse scheduled time
    parsed_time = None
    if scheduled_time:
        try:
            parsed_time = datetime.fromisoformat(scheduled_time)
        except ValueError:
            return JSONResponse({"error": "Invalid scheduled time format"}, status_code=400)
    
    # At least one of scheduled_time or recurring_minutes must be set
    if not parsed_time and recurring_minutes <= 0:
        return JSONResponse({"error": "Must specify either scheduled time or recurring interval"}, status_code=400)
    
    task_id = await task_scheduler.add_task(
        task_type=task_type,
        name=name,
        message=message,
        channel_id=channel_id,
        scheduled_time=parsed_time,
        recurring_minutes=recurring_minutes
    )
    
    return JSONResponse({"success": True, "task_id": task_id})


@router.put("/api/tasks/{task_id}")
async def update_task(
    request: Request,
    task_id: str,
    name: str = Form(None),
    message: str = Form(None),
    channel_id: int = Form(None),
    scheduled_time: str = Form(None),
    recurring_minutes: int = Form(None),
    enabled: bool = Form(None)
) -> JSONResponse:
    """Update an existing task."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    updates = {}
    if name is not None:
        updates["name"] = name
    if message is not None:
        updates["message"] = message
    if channel_id is not None:
        updates["channel_id"] = channel_id
    if scheduled_time is not None:
        if scheduled_time:
            try:
                updates["scheduled_time"] = datetime.fromisoformat(scheduled_time)
            except ValueError:
                return JSONResponse({"error": "Invalid scheduled time format"}, status_code=400)
        else:
            updates["scheduled_time"] = None
    if recurring_minutes is not None:
        updates["recurring_minutes"] = recurring_minutes
    if enabled is not None:
        updates["enabled"] = enabled
    
    success = await task_scheduler.update_task(task_id, **updates)
    
    if not success:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    return JSONResponse({"success": True})


@router.delete("/api/tasks/{task_id}")
async def delete_task(request: Request, task_id: str) -> JSONResponse:
    """Delete a scheduled task."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    success = await task_scheduler.delete_task(task_id)
    
    if not success:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    return JSONResponse({"success": True})


@router.post("/api/tasks/{task_id}/toggle")
async def toggle_task(request: Request, task_id: str) -> JSONResponse:
    """Toggle a task's enabled state."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    success = await task_scheduler.toggle_task(task_id)
    
    if not success:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    return JSONResponse({"success": True})


@router.post("/api/tasks/{task_id}/run")
async def run_task_now(request: Request, task_id: str) -> JSONResponse:
    """Run a task immediately."""
    token = get_session_token(request)
    if not validate_session(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    task = await task_scheduler.get_task(task_id)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    success, error = await task_scheduler.execute_task(task)
    
    if not success:
        return JSONResponse({"error": str(error)}, status_code=500)
    
    return JSONResponse({"success": True})
