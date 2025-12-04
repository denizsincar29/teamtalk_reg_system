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

# Session expiry time
SESSION_EXPIRY_HOURS = 8


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
        "expires": datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)
    }
    return token


def validate_session(token: str | None) -> str | None:
    """Validate session token and return username if valid."""
    if not token:
        return None
    session = admin_sessions.get(token)
    if not session:
        return None
    if datetime.now() > session["expires"]:
        del admin_sessions[token]
        return None
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
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "lang": lang,
            "t": t,
            "username": html.escape(username)
        })
    
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
        max_age=SESSION_EXPIRY_HOURS * 3600,
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
