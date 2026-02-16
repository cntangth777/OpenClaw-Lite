import json
import os
import hashlib
from typing import Dict, Any, Optional

class ConfigManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(self.data_dir, "config.json")
        self.memory_file = os.path.join(self.data_dir, "memory.json")
        self._ensure_data_dir()
        self.config = self._load_config()

    def _ensure_data_dir(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _default_config(self) -> Dict[str, Any]:
        return {
            "admin_password": "niujiazheng",  # Initial default password
            "is_setup_complete": False,       # Flag to track if user has configured the bot
            
            # AI Configuration
            "openai_api_base": "https://api.openai.com/v1",
            "openai_api_key": "",
            "model_name": "gpt-3.5-turbo",
            
            # Telegram Configuration
            "telegram_bot_token": "",
            "telegram_webhook_url": "",
            
            # Bot Personality
            "system_prompt": "You are JiazhengBot, a helpful AI assistant. You have access to a browser tool to search the web, summarize content, and translate it.",
            
            # Browser Configuration
            "browser_enabled": True
        }

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_file):
            return self._default_config()
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return self._default_config()

    def save_config(self, new_config: Optional[Dict[str, Any]] = None):
        if new_config:
            self.config.update(new_config)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def verify_password(self, password: str) -> bool:
        # In a real production app, we would hash this. 
        # For this "Lite" version, we verify against the stored string.
        return password == self.config.get("admin_password")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save_config()

config_manager = ConfigManager()
