import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import CHATS_DIR

from app.services.vector_store import vector_store


class ChatService:
    @staticmethod
    def get_or_create_session(session_id: Optional[str] = None) -> str:
        if not session_id or ".." in session_id or "/" in session_id:
            return str(uuid.uuid4())
        return session_id

    @staticmethod
    def get_history(session_id: str) -> List[Dict[str, Any]]:
        path = os.path.join(CHATS_DIR, f"chat_{session_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("messages", [])
        return []

    @staticmethod
    def save_message(session_id: str, role: str, content: str) -> None:
        path = os.path.join(CHATS_DIR, f"chat_{session_id}.json")
        data: Dict[str, Any] = {"messages": []}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["messages"].append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        vector_store.add_memory(role, content)

    @staticmethod
    def list_sessions() -> List[Dict[str, Any]]:
        sessions = []
        if os.path.exists(CHATS_DIR):
            import glob

            for file_path in glob.glob(os.path.join(CHATS_DIR, "chat_*.json")):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    messages = data.get("messages", [])
                    if messages:
                        sid = (
                            os.path.basename(file_path)
                            .replace("chat_", "")
                            .replace(".json", "")
                        )
                        title = next(
                            (m["content"] for m in messages if m["role"] == "user"),
                            "New Conversation",
                        )
                        timestamp = messages[-1].get("timestamp", "")
                        sessions.append(
                            {
                                "id": sid,
                                "title": title[:35]
                                + ("..." if len(title) > 35 else ""),
                                "timestamp": timestamp,
                            }
                        )
                except Exception:
                    pass
        return sorted(sessions, key=lambda x: x["timestamp"], reverse=True)
