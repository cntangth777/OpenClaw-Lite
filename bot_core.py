import json
import os
import openai
from config_manager import ConfigManager
from browser_tool import BrowserTool
from datetime import datetime

class BotCore:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.browser_tool = BrowserTool(headless=True)
        self.history = []
        self._load_memory()

    def _load_memory(self):
        """Loads conversation history from disk."""
        memory_file = self.config_manager.memory_file
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get("history", [])
            except Exception:
                self.history = []

    def save_memory(self):
        """Saves conversation history to disk."""
        memory_file = self.config_manager.memory_file
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump({"history": self.history}, f, ensure_ascii=False, indent=2)

    def _get_api_client(self):
        """Initializes OpenAI client with current config."""
        api_key = self.config_manager.get("openai_api_key")
        base_url = self.config_manager.get("openai_api_base")
        if not api_key:
            return None
        return openai.OpenAI(api_key=api_key, base_url=base_url)

    async def chat(self, user_input: str) -> str:
        """Process user input and generate a response."""
        client = self._get_api_client()
        if not client:
            return "⚠️ Please configure your OpenAI API Key in the settings first."

        # Add user message to history
        self.history.append({"role": "user", "content": user_input, "timestamp": datetime.now().isoformat()})
        
        # Check for URL in message (Simple heuristic)
        urls = [word for word in user_input.split() if word.startswith("http")]
        context_content = ""
        
        if urls and self.config_manager.get("browser_enabled"):
            url = urls[0]
            context_content = f"The user provided a URL: {url}. I will browse it for you.\n"
            # Browser action
            page_data = await self.browser_tool.fetch_page_content(url)
            if page_data.get("error"):
                context_content += f"Failed to fetch {url}: {page_data['error']}"
            else:
                context_content += f"Page Title: {page_data['title']}\nPage Content Summary: {page_data['text'][:2000]}..." # Truncate for token saving
                
            # Add explicit system instruction for this turn
            self.history.append({"role": "system", "content": f"Browser Context: {context_content}", "timestamp": datetime.now().isoformat()})

        # Prepare messages for API
        system_prompt = self.config_manager.get("system_prompt")
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history (simple sliding window or full history, maybe limit last 10)
        recent_history = self.history[-10:] if len(self.history) > 10 else self.history
        for msg in recent_history:
            if msg["role"] in ["user", "assistant", "system"]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        try:
            response = client.chat.completions.create(
                model=self.config_manager.get("model_name"),
                messages=messages
            )
            reply = response.choices[0].message.content
        except Exception as e:
            reply = f"Error generating response: {str(e)}"

        # Add assistant response to history
        self.history.append({"role": "assistant", "content": reply, "timestamp": datetime.now().isoformat()})
        self.save_memory()
        
        return reply

    def get_history(self):
        return self.history

    def clear_history(self):
        self.history = []
        self.save_memory()
