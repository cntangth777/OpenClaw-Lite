from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import secrets
import logging
from config_manager import ConfigManager
from bot_core import BotCore
from telegram_bot import TelegramBot

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Core Components
config_manager = ConfigManager()
bot_core = BotCore(config_manager)
telegram_bot = TelegramBot(config_manager)

app = FastAPI(title="OpenClaw-Lite", docs_url=None, redoc_url=None)

# Session Middleware (Secret key should be persistent in prod, random for now is okay for single instance restart)
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))

# Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependencies
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return user

def require_auth(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=302, detail="Not authenticated", headers={"Location": "/login"})
    return user

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not config_manager.get("is_setup_complete"):
        return RedirectResponse(url="/setup", status_code=302)
    
    user = request.session.get("user")
    if user:
        return RedirectResponse(url="/chat", status_code=302)
    return RedirectResponse(url="/login", status_code=302)

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    if config_manager.get("is_setup_complete"):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("setup.html", {"request": request})

@app.post("/setup")
async def setup_action(request: Request, password: str = Form(...)):
    # In this minimal version, we accept the password provided as the admin password
    # "Only input once" logic: we set the password now.
    config_manager.set("admin_password", password)
    config_manager.set("is_setup_complete", True)
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_action(request: Request, password: str = Form(...)):
    if config_manager.verify_password(password):
        request.session["user"] = "admin"
        return RedirectResponse(url="/chat", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid Password"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin.html", {"request": request, "config": config_manager.config})

# API Routes
@app.post("/api/chat")
async def api_chat(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    data = await request.json()
    user_message = data.get("message")
    if not user_message:
        return JSONResponse({"error": "Empty message"}, status_code=400)
        
    reply = await bot_core.chat(user_message)
    return JSONResponse({"reply": reply})

@app.get("/api/history")
async def api_history(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return JSONResponse({"history": bot_core.get_history()})

@app.post("/api/config")
async def api_config(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
    data = await request.json()
    # Update config
    for key, value in data.items():
        if key in config_manager.config:
             config_manager.set(key, value)
    
    # Handle Telegram Webhook update if token/url changed
    if "telegram_bot_token" in data or "telegram_webhook_url" in data:
        webhook_url = data.get("telegram_webhook_url", config_manager.get("telegram_webhook_url"))
        if webhook_url:
            await telegram_bot.set_webhook(webhook_url)
            
    return JSONResponse({"status": "success"})

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            
            if text:
                # Process with BotCore
                # Reply to Telegram (Simplistic: no history context per user in this Lite version, 
                # or we assume single user for Personal Bot)
                # OpenClaw concept: "Personal Assistant" -> Single User. 
                # We will treat Telegram input as "User" input to the main bot.
                
                # Ideally we want to know WHO is talking. For "Personal Bot", maybe allow only specific ID.
                # For now, simplistic: everyone talks to the same bot instance (shared memory) or we ignore memory.
                # OpenClaw-Lite: Let's share memory for simplicity or just run statelessly.
                # BotCore saves history.
                
                reply = await bot_core.chat(f"[Telegram] {text}")
                await telegram_bot.send_message(chat_id, reply)
                
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse({"status": "error"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
