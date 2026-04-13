import json
from typing import Any, AsyncIterator, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from config import GROQ_MODEL, SYSTEM_PROMPT

from app.services.chat_service import ChatService
from app.services.vector_store import vector_store
from app.utils.time_info import time_context_block


class GroqService:
    @staticmethod
    def _format_history(history: List[Dict[str, Any]]) -> List[Any]:
        msgs = []
        for h in history[-10:]:
            if h["role"] == "user":
                msgs.append(HumanMessage(content=h["content"]))
            elif h["role"] == "assistant":
                msgs.append(AIMessage(content=h["content"]))
        return msgs

    @staticmethod
    def _build_system_message(context: str, extra: str = "") -> str:
        mem_block = (
            f"\n\n[CRITICAL SYSTEM MEMORY]:\nThe following facts are retrieved from your database. Treat them as absolute truth:\n{context}\n"
            if context
            else ""
        )
        return SYSTEM_PROMPT + time_context_block() + mem_block + extra

    @staticmethod
    async def stream_general(
        message: str, session_id: str, api_key: str
    ) -> AsyncIterator[str]:
        ChatService.save_message(session_id, "user", message)
        context = vector_store.search(message)
        sys_msg = GroqService._build_system_message(context)

        chat = ChatGroq(temperature=0.7, model_name=GROQ_MODEL, groq_api_key=api_key)
        history_dicts = ChatService.get_history(session_id)[:-1]
        messages = (
            [SystemMessage(content=sys_msg)]
            + GroqService._format_history(history_dicts)
            + [HumanMessage(content=message)]
        )

        full_response = ""
        try:
            for chunk in chat.stream(messages):
                if chunk.content:
                    full_response += chunk.content
                    yield chunk.content
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate" in error_msg.lower():
                yield json.dumps({"error": "rate_limit", "message": "Groq rate limit reached. Please wait a moment and try again."})
            else:
                yield json.dumps({"error": "unknown", "message": error_msg})
            return

        ChatService.save_message(session_id, "assistant", full_response)

    @staticmethod
    async def invoke_general(message: str, session_id: str, api_key: str) -> str:
        text = ""
        async for part in GroqService.stream_general(message, session_id, api_key):
            text += part
        return text
