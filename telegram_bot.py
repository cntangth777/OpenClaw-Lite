import httpx
import logging
from config_manager import ConfigManager

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.api_base = "https://api.telegram.org/bot"

    def _get_token(self):
        return self.config_manager.get("telegram_bot_token")

    async def set_webhook(self, webhook_url: str) -> bool:
        token = self._get_token()
        if not token:
            logger.error("No Telegram token set.")
            return False
            
        url = f"{self.api_base}{token}/setWebhook"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json={"url": webhook_url})
                result = response.json()
                if result.get("ok"):
                    logger.info(f"Webhook set to {webhook_url}")
                    return True
                else:
                    logger.error(f"Failed to set webhook: {result}")
                    return False
        except Exception as e:
            logger.error(f"Exception setting webhook: {e}")
            return False

    async def send_message(self, chat_id: int, text: str) -> bool:
        token = self._get_token()
        if not token:
            return False
            
        url = f"{self.api_base}{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(url, json=payload)
                return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def delete_webhook(self) -> bool:
        token = self._get_token()
        if not token:
            return False
            
        url = f"{self.api_base}{token}/deleteWebhook"
        try:
            async with httpx.AsyncClient() as client:
                await client.get(url)
                return True
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False
