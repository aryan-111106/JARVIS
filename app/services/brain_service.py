import re

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from config import GROQ_BRAIN_MODEL, TAVILY_API_KEY


class BrainService:
    _IMAGE_PAT = re.compile(
        r"(generate|draw|create|make)\s+(an?\s+)?(image|picture|photo|art)\s+of",
        re.IGNORECASE,
    )
    _ACTION_PAT = re.compile(
        r"(?:please\s+|can\s+you\s+|jarvis,\s+)?\b(open|launch|start|run|show)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def _quick_image_gen(message: str) -> bool:
        if BrainService._IMAGE_PAT.search(message):
            return True
        low = message.lower()
        return "generate an image" in low or "draw me" in low

    @staticmethod
    def _quick_action(message: str) -> bool:
        """Heuristic: explicit open/launch/start/run commands go to task executor."""
        return bool(BrainService._ACTION_PAT.search(message.strip()))

    @staticmethod
    async def classify_intent(message: str, api_key: str) -> str:
        """
        Returns: general | realtime | action | image_gen
        (Vision is chosen when an image is attached; not classified here.)
        """
        if BrainService._quick_image_gen(message):
            return "image_gen"
        if BrainService._quick_action(message):
            return "action"

        chat = ChatGroq(
            temperature=0, model_name=GROQ_BRAIN_MODEL, groq_api_key=api_key
        )

        prompt = f"""You are the routing brain of JARVIS. Classify the user's query into EXACTLY ONE category:

1. 'action' : User explicitly commands you to OPEN, LAUNCH, or START a website, app, or YouTube search.
   Examples: "open youtube", "launch calculator", "start spotify", "open google"

2. 'image_gen' : User wants you to CREATE or GENERATE an image, picture, drawing, or art.
   Examples: "generate an image of a cat", "draw a sunset"

3. 'realtime' : User asks ANY question about facts, people, news, weather, prices, sports, history, or anything that needs up-to-date web information.
   Examples: "who is elon musk?", "bitcoin price?", "who won the match?"

4. 'general' : Greetings, casual chat, coding/math help, creative writing without needing live web data, or questions answerable from memory alone.

Query: "{message}"
Output ONLY one word: action, image_gen, realtime, or general — nothing else."""

        try:
            res = chat.invoke([HumanMessage(content=prompt)])
            intent = (res.content or "").lower().strip()
            first_token = (intent.split() or [""])[0].strip(".,!\"'")

            if first_token == "action":
                return "action"
            if first_token == "image_gen":
                return "image_gen"
            if first_token == "realtime" and TAVILY_API_KEY:
                return "realtime"

            msg_lower = message.lower()
            if (
                any(
                    q in msg_lower
                    for q in ["who is", "what is", "where is", "tell me about"]
                )
                and TAVILY_API_KEY
            ):
                return "realtime"

            return "general"
        except Exception:
            return "general"
