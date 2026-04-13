from typing import Tuple

from config import GROQ_API_KEYS


class KeyManager:
    """Rotate between multiple Groq API keys (brain vs chat use different slots when possible)."""

    def __init__(self):
        self.keys = GROQ_API_KEYS
        self.brain_idx = 0
        self.chat_idx = 1 if len(self.keys) > 1 else 0

    def get_keys(self) -> Tuple[str, str]:
        if not self.keys:
            raise ValueError("No GROQ_API_KEY found in environment.")
        brain_key = self.keys[self.brain_idx]
        chat_key = self.keys[self.chat_idx]

        if len(self.keys) > 1:
            self.brain_idx = (self.brain_idx + 1) % len(self.keys)
            self.chat_idx = (self.chat_idx + 1) % len(self.keys)
            if self.brain_idx == self.chat_idx:
                self.chat_idx = (self.chat_idx + 1) % len(self.keys)

        return brain_key, chat_key


key_manager = KeyManager()
