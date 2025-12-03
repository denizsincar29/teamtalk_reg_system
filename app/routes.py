"""FastAPI routes for the registration system."""

import base64
import html
from pathlib import Path

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from fastapi.templating import Jinja2Templates

from .config import MIN_PASSWORD_LENGTH, MIN_USERNAME_LENGTH
from .i18n import DEFAULT_LANGUAGE, LANGUAGES, get_translation, get_translations
from .manager import tt_manager
from .tt_file import generate_tt_file, generate_tt_url, get_server_info

router = APIRouter()

# Set up templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


def get_lang(lang: str | None) -> str:
    """Get valid language code."""
    if lang and lang in LANGUAGES:
        return lang
    return DEFAULT_LANGUAGE


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, lang: str = Query(default=None)) -> HTMLResponse:
    """Render the registration form."""
    lang = get_lang(lang)
    t = get_translations(lang)
    return templates.TemplateResponse("base.html", {
        "request": request,
        "message": "",
        "lang": lang,
        "t": t
    })


@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    lang: str = Query(default=None)
) -> HTMLResponse:
    """Handle user registration.
    
    Args:
        request: The FastAPI request object.
        username: The desired username.
        password: The desired password.
        lang: Language code for translations.
        
    Returns:
        HTML response with success or error message.
    """
    lang = get_lang(lang)
    t = get_translations(lang)
    
    # Clean and validate input
    username = username.strip()
    password = password.strip()
    
    if not username or not password:
        error_msg = get_translation(lang, "error_required")
        message = f'<div class="message error">{error_msg}</div>'
        return templates.TemplateResponse("base.html", {
            "request": request, "message": message, "lang": lang, "t": t
        })
    
    if len(username) < MIN_USERNAME_LENGTH:
        error_msg = get_translation(lang, "error_username_short", min_length=MIN_USERNAME_LENGTH)
        message = f'<div class="message error">{error_msg}</div>'
        return templates.TemplateResponse("base.html", {
            "request": request, "message": message, "lang": lang, "t": t
        })
    
    if len(password) < MIN_PASSWORD_LENGTH:
        error_msg = get_translation(lang, "error_password_short", min_length=MIN_PASSWORD_LENGTH)
        message = f'<div class="message error">{error_msg}</div>'
        return templates.TemplateResponse("base.html", {
            "request": request, "message": message, "lang": lang, "t": t
        })
    
    # Check if user already exists
    exists, error = await tt_manager.check_user_exists(username)
    
    if error:
        escaped_error = html.escape(str(error))
        error_msg = get_translation(lang, "error_checking_user", error=escaped_error)
        message = f'<div class="message error">{error_msg}</div>'
        return templates.TemplateResponse("base.html", {
            "request": request, "message": message, "lang": lang, "t": t
        })
    
    if exists:
        error_msg = get_translation(lang, "error_user_exists")
        message = f'<div class="message error">{error_msg}</div>'
        return templates.TemplateResponse("base.html", {
            "request": request, "message": message, "lang": lang, "t": t
        })
    
    # Create the user
    success, error = await tt_manager.create_user(username, password)
    
    if success:
        # Redirect to success page with download options
        server_info = get_server_info()
        tt_url = generate_tt_url(username, password)
        # Encode password for URL (base64)
        password_encoded = base64.urlsafe_b64encode(password.encode()).decode()
        # Pre-format the success message with username
        success_msg = get_translation(lang, "success_message", username=html.escape(username))
        download_btn = get_translation(lang, "download_button", username=html.escape(username))
        
        return templates.TemplateResponse("success.html", {
            "request": request,
            "username": html.escape(username),
            "password_encoded": password_encoded,
            "tt_url": tt_url,
            "host": server_info["host"],
            "tcp_port": server_info["tcp_port"],
            "udp_port": server_info["udp_port"],
            "lang": lang,
            "t": t,
            "success_msg": success_msg,
            "download_btn": download_btn
        })
    else:
        escaped_error = html.escape(str(error))
        error_msg = get_translation(lang, "error_create_failed", error=escaped_error)
        message = f'<div class="message error">{error_msg}</div>'
        return templates.TemplateResponse("base.html", {
            "request": request, "message": message, "lang": lang, "t": t
        })


@router.get("/download-tt/{username}/{password_encoded}")
async def download_tt_file(username: str, password_encoded: str) -> Response:
    """Generate and download a .tt configuration file.
    
    Args:
        username: The username for the .tt file.
        password_encoded: Base64-encoded password.
        
    Returns:
        .tt file as download response.
    """
    try:
        # Decode password from base64
        password = base64.urlsafe_b64decode(password_encoded.encode()).decode()
        
        # Generate .tt file content
        tt_content = generate_tt_file(username, password)
        
        # Return as downloadable file
        return Response(
            content=tt_content,
            media_type="application/x-teamtalk",
            headers={
                "Content-Disposition": f'attachment; filename="{username}.tt"'
            }
        )
    except Exception as e:
        return Response(
            content=f"Error generating .tt file: {str(e)}",
            status_code=400
        )


@router.get("/api/broadcast")
async def broadcast_test() -> JSONResponse:
    """Test endpoint to send a broadcast message.
    
    This endpoint sends a test broadcast message to all users on the server.
    
    Returns:
        JSON response with success status.
    """
    success, error = await tt_manager.send_broadcast("Test broadcast from registration system")
    
    if success:
        return JSONResponse({"success": True, "message": "Broadcast sent successfully"})
    else:
        return JSONResponse({"success": False, "error": error}, status_code=500)
