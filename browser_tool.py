import asyncio
from playwright.async_api import async_playwright
import os

class BrowserTool:
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def fetch_page_content(self, url: str) -> dict:
        """
        Navigates to a URL and extracts text content and title.
        Returns a dictionary with 'title', 'text', and 'url'.
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless, args=["--no-sandbox", "--disable-setuid-sandbox"])
                page = await browser.new_page()
                
                # Set a realistic user agent
                await page.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                
                # Get extraction
                title = await page.title()
                # Simple extraction: get body text. In a real scenario, use readability.js or similar.
                # For now, we'll just get innerText of body to be safe and simple.
                text = await page.evaluate("document.body.innerText")
                
                await browser.close()
                
                return {
                    "title": title,
                    "text": text[:50000], # Limit content to avoid context overflow issues downstream
                    "url": url,
                    "error": None
                }
        except Exception as e:
            return {
                "title": "Error",
                "text": "",
                "url": url,
                "error": str(e)
            }

    async def take_screenshot(self, url: str, output_path: str) -> bool:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless, args=["--no-sandbox"])
                page = await browser.new_page()
                await page.goto(url, timeout=30000, wait_until="networkidle")
                await page.screenshot(path=output_path, full_page=True)
                await browser.close()
                return True
        except Exception as e:
            print(f"Screenshot error: {e}")
            return False
