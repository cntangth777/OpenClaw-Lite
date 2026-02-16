# 🦞 OpenClaw-Lite (JiazhengBot)

Bot based on FastAPI + Playwright + OpenAI, deployable on HuggingFace Spaces.

## Features
- **Browser Tool**: Can browse web pages, summarize content, and take screenshots using Playwright.
- **Telegram Integration**: Chat directly via Telegram Bot (Webhook mode).
- **Admin Panel**: Configure API keys, prompts, and view history.
- **Secure**: Password protected admin area (Initial setup required).

## Deployment on HuggingFace Spaces

1. Create a new Space on HuggingFace.
   - SDK: **Docker**
   - Template: **Blank**

2. Clone this repository locally.

3. Push the code to your HuggingFace Space repository.

4. The Space will build and start automatically.

## Setup

1. Once deployed, open the App URL.
2. You will be redirected to the **Setup** page.
3. Enter your desired **Admin Password** (Default suggestion: `niujiazheng`).
4. Login with the password.

## Configuration

1. Go to the **Settings** (Admin) panel.
2. Enter your **OpenAI API Key** and **Base URL**.
3. (Optional) Enter your **Telegram Bot Token**.
4. (Optional) Enter your **Telegram Webhook URL** (The URL of your HuggingFace Space + `/webhook`, e.g., `https://huggingface.co/spaces/username/space-name/webhook`).
5. Save configuration.

## Usage

- **Web Chat**: Use the built-in chat interface.
- **Telegram**: Chat with your bot on Telegram.
- **Browser Tool**: Send a URL in the chat (e.g., "Summarize https://example.com"), and the bot will visit it.
