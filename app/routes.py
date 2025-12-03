"""FastAPI routes for the registration system."""

import html
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .config import MIN_PASSWORD_LENGTH, MIN_USERNAME_LENGTH
from .manager import tt_manager

router = APIRouter()

# Set up templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the registration form."""
    return templates.TemplateResponse("base.html", {"request": request, "message": ""})


@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
) -> HTMLResponse:
    """Handle user registration.
    
    Args:
        request: The FastAPI request object.
        username: The desired username.
        password: The desired password.
        
    Returns:
        HTML response with success or error message.
    """
    # Clean and validate input
    username = username.strip()
    password = password.strip()
    
    if not username or not password:
        message = '<div class="message error">Username and password are required.</div>'
        return templates.TemplateResponse("base.html", {"request": request, "message": message})
    
    if len(username) < MIN_USERNAME_LENGTH:
        message = f'<div class="message error">Username must be at least {MIN_USERNAME_LENGTH} characters.</div>'
        return templates.TemplateResponse("base.html", {"request": request, "message": message})
    
    if len(password) < MIN_PASSWORD_LENGTH:
        message = f'<div class="message error">Password must be at least {MIN_PASSWORD_LENGTH} characters.</div>'
        return templates.TemplateResponse("base.html", {"request": request, "message": message})
    
    # Check if user already exists
    exists, error = await tt_manager.check_user_exists(username)
    
    if error:
        escaped_error = html.escape(str(error))
        message = f'<div class="message error">Error checking user: {escaped_error}</div>'
        return templates.TemplateResponse("base.html", {"request": request, "message": message})
    
    if exists:
        message = '<div class="message error">Username already exists. Please choose another.</div>'
        return templates.TemplateResponse("base.html", {"request": request, "message": message})
    
    # Create the user
    success, error = await tt_manager.create_user(username, password)
    
    if success:
        escaped_username = html.escape(username)
        message = f'<div class="message success">User "{escaped_username}" registered successfully! You can now connect to the TeamTalk server.</div>'
        return templates.TemplateResponse("base.html", {"request": request, "message": message})
    else:
        escaped_error = html.escape(str(error))
        message = f'<div class="message error">Failed to create user: {escaped_error}</div>'
        return templates.TemplateResponse("base.html", {"request": request, "message": message})
