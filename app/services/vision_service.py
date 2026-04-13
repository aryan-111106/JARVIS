from typing import Any, AsyncIterator, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from config import GROQ_VISION_MODEL, SYSTEM_PROMPT

from app.services.chat_service import ChatService
from app.services.vector_store import vector_store
from app.utils.time_info import time_context_block


class VisionService:
    @staticmethod
    def _format_history(history: List[Dict[str, Any]]) -> List[Any]:
        msgs = []
        for h in history[-6:]:
            if h["role"] == "user":
                msgs.append(HumanMessage(content=h["content"]))
            elif h["role"] == "assistant":
                msgs.append(AIMessage(content=h["content"]))
        return msgs

    @staticmethod
    def _data_url(mime: str, b64: str) -> str:
        m = mime or "image/jpeg"
        return f"data:{m};base64,{b64}"

    @staticmethod
    async def stream_vision(
        message: str,
        image_base64: str,
        mime: str,
        session_id: str,
        api_key: str,
    ) -> AsyncIterator[str]:
        # Strip data URL prefix if present
        raw = image_base64
        if "base64," in raw:
            raw = raw.split("base64,", 1)[1]
        raw = raw.strip()

        user_text = message.strip() if message.strip() else "Describe this image and answer any implied questions."
        user_display = f"{user_text}\n[Image attached]"
        ChatService.save_message(session_id, "user", user_display)

        context = vector_store.search(user_text)
        mem_block = (
            f"\n\n[CRITICAL SYSTEM MEMORY]:\n{context}\n" if context else ""
        )
        sys_content = (
            SYSTEM_PROMPT
            + time_context_block()
            + mem_block
            + "\nYou are analyzing an image the user provided. Be specific and helpful."
        )

        data_url = VisionService._data_url(mime, raw)
        human = HumanMessage(
            content=[
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
        )

        chat = ChatGroq(
            temperature=0.5,
            model_name=GROQ_VISION_MODEL,
            groq_api_key=api_key,
        )
        history_dicts = ChatService.get_history(session_id)[:-1]
        messages = (
            [SystemMessage(content=sys_content)]
            + VisionService._format_history(history_dicts)
            + [human]
        )

        full_response = ""
        for chunk in chat.stream(messages):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        ChatService.save_message(session_id, "assistant", full_response)
