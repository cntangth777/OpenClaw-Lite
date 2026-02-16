import os
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright
import openai

app = FastAPI()

# 内存配置 (实际应存入数据库，这里简化为全局变量)
CONFIG = {
    "admin_password": "",
    "tg_token": "",
    "llm_api_key": "",
    "llm_base_url": "https://api.openai.com/v1",
    "is_initialized": False
}

# --- 核心功能：浏览器总结 ---
async def browse_and_summarize(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        content = await page.content()
        # 简单提取文本
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()[:4000] # 截取前4000字防止溢出
        await browser.close()
        
        # 调用大模型总结
        client = openai.AsyncOpenAI(api_key=CONFIG["llm_api_key"], base_url=CONFIG["llm_base_url"])
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo", # 或你指定的模型
            messages=[
                {"role": "system", "content": "你是一个翻译官和总结专家。请将用户提供的网页内容总结成精炼的中文，并分条列出。"},
                {"role": "user", "content": f"URL: {url}\n内容: {text}"}
            ]
        )
        return response.choices[0].message.content

# --- Telegram Bot 处理 ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith("http"):
        await update.message.reply_text("🔍 正在打开浏览器抓取并分析网页，请稍候...")
        try:
            summary = await browse_and_summarize(text)
            await update.message.reply_text(f"📋 **网页总结：**\n\n{summary}", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ 出错了: {str(e)}")
    else:
        # 普通聊天逻辑
        client = openai.AsyncOpenAI(api_key=CONFIG["llm_api_key"], base_url=CONFIG["llm_base_url"])
        res = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": text}]
        )
        await update.message.reply_text(res.choices[0].message.content)

# --- 后台路由 ---
@app.get("/", response_class=HTMLResponse)
async def admin_page():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/config")
async def save_config(password: str = Form(...), tg_token: str = Form(...), api_key: str = Form(...)):
    if not CONFIG["is_initialized"]:
        CONFIG["admin_password"] = password
        CONFIG["is_initialized"] = True
    elif password != CONFIG["admin_password"]:
        return JSONResponse({"status": "error", "message": "密码错误"})
    
    CONFIG["tg_token"] = tg_token
    CONFIG["llm_api_key"] = api_key
    
    # 启动 Telegram Bot
    asyncio.create_task(run_tg_bot())
    return {"status": "success", "message": "配置已保存，Bot 已启动"}

async def run_tg_bot():
    application = Application.builder().token(CONFIG["tg_token"]).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
