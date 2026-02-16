import os
import json
import asyncio
import logging
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import openai

# --- 基础配置 ---
logging.basicConfig(level=logging.INFO)
app = FastAPI()
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"password": "", "tg_token": "", "api_key": "", "base_url": "https://api.openai.com/v1", "is_init": False}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# --- 核心技能：网页总结翻译 ---
async def smart_browse(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            # 过滤掉脚本和样式，只取正文
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=' ', strip=True)[:5000]
            await browser.close()
            
            config = load_config()
            client = openai.AsyncOpenAI(api_key=config["api_key"], base_url=config["base_url"])
            response = await client.chat.completions.create(
                model="gpt-4o-mini", # 建议使用更强的模型进行总结
                messages=[
                    {"role": "system", "content": "你是一个精通多国语言的AI助手。请分析网页内容，给出核心摘要，并将其翻译成优雅的中文。格式：[标题]\n[核心摘要]\n[翻译结论]"},
                    {"role": "user", "content": f"URL: {url}\n内容: {text}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"浏览器访问失败: {str(e)}"

# --- Telegram 逻辑 ---
async def handle_tg_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_text = update.message.text
    config = load_config()
    
    if msg_text.startswith("http"):
        await update.message.reply_text("🌐 正在使用内置浏览器访问网页并总结翻译...")
        res = await smart_browse(msg_text)
        await update.message.reply_text(res)
    else:
        client = openai.AsyncOpenAI(api_key=config["api_key"], base_url=config["base_url"])
        res = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": msg_text}]
        )
        await update.message.reply_text(res.choices[0].message.content)

# --- API 路由 ---
@app.get("/", response_class=HTMLResponse)
async def index():
    # 这里直接嵌入 HTML 代码，实现 OpenClaw 风格
    return """
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OpenClaw Lite - 控制面板</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0f172a; color: #e2e8f0; font-family: 'Inter', sans-serif; }
            .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
            input { background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 8px; width: 100%; margin-bottom: 15px; }
            button { background: #3b82f6; transition: 0.3s; }
            button:hover { background: #2563eb; transform: translateY(-2px); }
        </style>
    </head>
    <body class="flex flex-col items-center justify-center min-h-screen p-4">
        <div class="glass p-8 rounded-2xl w-full max-w-md shadow-2xl">
            <h1 class="text-3xl font-bold mb-6 text-center text-blue-400">OpenClaw Lite</h1>
            <div id="setup-form">
                <p class="text-sm text-slate-400 mb-4 text-center">首次部署请设置管理密码</p>
                <input type="password" id="admin_pwd" placeholder="设置管理密码">
                <input type="text" id="tg_token" placeholder="Telegram Bot Token">
                <input type="text" id="api_key" placeholder="LLM API Key">
                <input type="text" id="base_url" placeholder="API Base URL (可选)">
                <button onclick="saveConfig()" class="w-full py-3 rounded-xl font-bold">保存并启动机器人</button>
            </div>
            <div id="status-msg" class="mt-4 text-center text-green-400 hidden">配置已成功，Bot 已在后台运行！</div>
        </div>
        
        <script>
            async function saveConfig() {
                const data = new FormData();
                data.append('password', document.getElementById('admin_pwd').value);
                data.append('tg_token', document.getElementById('tg_token').value);
                data.append('api_key', document.getElementById('api_key').value);
                data.append('base_url', document.getElementById('base_url').value);
                
                const res = await fetch('/config', { method: 'POST', body: data });
                const result = await res.json();
                if(result.status === 'success') {
                    document.getElementById('status-msg').classList.remove('hidden');
                } else {
                    alert(result.message);
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/config")
async def update_config(password: str = Form(...), tg_token: str = Form(...), api_key: str = Form(...), base_url: str = Form(None)):
    config = load_config()
    if config["is_init"] and password != config["password"]:
        return {"status": "error", "message": "密码不正确"}
    
    config.update({
        "password": password,
        "tg_token": tg_token,
        "api_key": api_key,
        "base_url": base_url or "https://api.openai.com/v1",
        "is_init": True
    })
    save_config(config)
    
    # 异步启动 Bot
    asyncio.create_task(start_bot(tg_token))
    return {"status": "success", "message": "配置更新成功"}

async def start_bot(token):
    application = Application.builder().token(token).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tg_message))
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
