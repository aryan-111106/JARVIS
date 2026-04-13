import json
from typing import Any, AsyncIterator, Dict, List

import httpx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from config import (
    GROQ_BRAIN_MODEL,
    GROQ_MODEL,
    SYSTEM_PROMPT,
    TAVILY_API_KEY,
    TAVILY_MAX_RESULTS,
)

from app.services.chat_service import ChatService
from app.services.vector_store import vector_store
from app.utils.time_info import time_context_block


class RealtimeService:
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
    async def extract_search_query(message: str, api_key: str) -> str:
        """Turn conversational text into a concise Tavily query."""
        chat = ChatGroq(
            temperature=0, model_name=GROQ_BRAIN_MODEL, groq_api_key=api_key
        )
        prompt = f"""Convert the user's message into a concise web search query (3-14 words).
Output ONLY the query text. No quotes, no explanation.

User message: {message}
Search query:"""
        try:
            res = chat.invoke([HumanMessage(content=prompt)])
            q = (res.content or "").strip().strip('"').strip("'")
            return q if len(q) > 2 else message
        except Exception:
            return message

    @staticmethod
    async def stream_realtime(
        message: str, session_id: str, api_key: str
    ) -> AsyncIterator[str]:
        ChatService.save_message(session_id, "user", message)
        search_query = await RealtimeService.extract_search_query(message, api_key)

        search_context = ""
        if TAVILY_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": TAVILY_API_KEY,
                            "query": search_query,
                            "search_depth": "advanced",
                            "include_answer": True,
                            "max_results": TAVILY_MAX_RESULTS,
                        },
                    )
                    data = resp.json()
                    print(f"[TAVILY] query={search_query!r} keys={list(data.keys())}")
                    ans = data.get("answer", "")
                    results = data.get("results", [])[: TAVILY_MAX_RESULTS]

                    if results:
                        yield f"__SEARCH_RESULTS__:{json.dumps(results)}"

                    results_text = "\n".join(
                        [f"- {r['title']}: {r['content']}" for r in results]
                    )
                    search_context = f"\n\n[WEB SEARCH RESULTS]:\nSummary: {ans}\nSources:\n{results_text}\n\nUse the web search results above to answer the user accurately."
            except Exception as e:
                print(f"Tavily Error: {e}")

        context = vector_store.search(message)
        sys_msg = RealtimeService._build_system_message(context, search_context)

        chat = ChatGroq(temperature=0.7, model_name=GROQ_MODEL, groq_api_key=api_key)
        history_dicts = ChatService.get_history(session_id)[:-1]
        messages = (
            [SystemMessage(content=sys_msg)]
            + RealtimeService._format_history(history_dicts)
            + [HumanMessage(content=message)]
        )

        full_response = ""
        for chunk in chat.stream(messages):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        ChatService.save_message(session_id, "assistant", full_response)

    @staticmethod
    async def invoke_realtime(message: str, session_id: str, api_key: str) -> str:
        text = ""
        async for part in RealtimeService.stream_realtime(
            message, session_id, api_key
        ):
            if not part.startswith("__SEARCH_RESULTS__:"):
                text += part
        return text
