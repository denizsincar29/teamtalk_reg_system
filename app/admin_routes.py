"""Admin panel routes for the TeamTalk Registration System."""

import html
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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
