import json
import os
import platform
import subprocess
import urllib.parse
import webbrowser

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from config import GROQ_BRAIN_MODEL

from app.services.chat_service import ChatService


def _extract_json_object(text: str) -> str | None:
    """Pull the first {...} block from model output if raw parse fails."""
    if not text:
        return None
    t = text.strip()
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        return t[start : end + 1]
    return None


_WIN_APP_ALIASES = {
    "calculator": "calc",
    "windows calculator": "calc",
    "file explorer": "explorer",
    "command prompt": "cmd",
    "paint": "mspaint",
    "microsoft paint": "mspaint",
    "settings": "ms-settings:",
    "windows settings": "ms-settings:",
    "terminal": "wt",
    "windows terminal": "wt",
    "notepad": "notepad",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "vs code": "code",
    "visual studio code": "code",
}


def _normalize_windows_app_target(target: str) -> str:
    key = (target or "").strip().lower()
    return _WIN_APP_ALIASES.get(key, (target or "").strip())


def _launch_windows_app(target: str) -> None:
    """
    Windows: use `cmd /c start "" <target>` so `start` gets a window title slot
    (required). Plain `os.system('start x')` is unreliable for some targets.
    """
    target = (target or "").strip()
    if not target:
        return
    # Single argument to `start`; empty "" is the window title placeholder.
    # Using list form to avoid shell quoting issues.
    subprocess.Popen(
        ["cmd", "/c", "start", "", target],
        shell=False,
        cwd=os.environ.get("USERPROFILE") or None,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )


class TaskExecutor:
    @staticmethod
    def pollinations_image_url(prompt: str) -> str:
        """
        Direct Pollinations image URL (JPEG).
        If POLLINATIONS_API_KEY is set, uses gen.pollinations.ai which requires it.
        Otherwise uses image.pollinations.ai (free stable endpoint).
        """
        from config import POLLINATIONS_API_KEY

        p = (prompt or "").strip()[:500]
        encoded = urllib.parse.quote(p, safe="")
        if POLLINATIONS_API_KEY:
            # gen.pollinations.ai often requires a key for better reliability/features
            return f"https://gen.pollinations.ai/prompt/{encoded}"
        return f"https://image.pollinations.ai/prompt/{encoded}"

    @staticmethod
    async def stream_image_generation(message: str, session_id: str, api_key: str):
        """Extract image prompt from user message, yield SSE markers + short confirmation."""
        ChatService.save_message(session_id, "user", message)
        chat = ChatGroq(
            temperature=0, model_name=GROQ_BRAIN_MODEL, groq_api_key=api_key
        )
        prompt = f"""The user wants to generate an image. Extract a concise English image description (max 200 chars) suitable for an image generator.
Respond ONLY with valid JSON: {{"prompt": "..."}}
User: {message}"""

        try:
            res = chat.invoke([HumanMessage(content=prompt)])
            raw = (res.content or "").replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            img_prompt = (data.get("prompt") or message).strip()
        except Exception:
            img_prompt = message.strip()

        url = TaskExecutor.pollinations_image_url(img_prompt)
        yield f"__IMAGE__:{json.dumps({'url': url, 'prompt': img_prompt})}"

        reply = f"Here is your image, Sir. I used Pollinations to create it from: {img_prompt}"
        yield reply
        ChatService.save_message(session_id, "assistant", reply)

    @staticmethod
    async def stream_action(message: str, session_id: str, api_key: str):
        ChatService.save_message(session_id, "user", message)
        chat = ChatGroq(
            temperature=0, model_name=GROQ_BRAIN_MODEL, groq_api_key=api_key
        )

        prompt = f"""The user wants to open an app, website, or YouTube. Extract the target from: "{message}"
Respond ONLY with valid JSON. No markdown.
Format:
{{"type": "website" or "app", "target": "value", "name": "Display Name"}}

Rules for 'target':
- Website: base domain like 'youtube.com' or full path for search e.g. 'youtube.com/results?search_query=cats'
- If user asks for YouTube search, use: youtube.com/results?search_query={{encoded query}}
- App (Windows): Calculator -> 'calc', Notepad -> 'notepad', Chrome -> 'chrome', Edge -> 'msedge', VS Code -> 'code', Paint -> 'mspaint', File Explorer -> 'explorer', Command Prompt -> 'cmd', Settings -> 'ms-settings:'

Query: "{message}"
"""

        try:
            res = chat.invoke([HumanMessage(content=prompt)])
            raw = (res.content or "").replace("```json", "").replace("```", "").strip()
            try:
                action_data = json.loads(raw)
            except json.JSONDecodeError:
                fallback = _extract_json_object(raw)
                if not fallback:
                    raise
                action_data = json.loads(fallback)

            action_type = (action_data.get("type") or "").lower()
            target = (action_data.get("target") or "").strip()
            name = action_data.get("name", "Application")

            if action_type == "app" and platform.system() == "Windows":
                target = _normalize_windows_app_target(target)

            if action_type == "website":
                if not target.startswith("http"):
                    target = "https://www." + target.replace("www.", "")

            yield f"__ACTION__:{json.dumps({'type': action_type, 'target': target, 'name': name})}"

            if action_type == "website":
                webbrowser.open(target)
            elif action_type == "app":
                system = platform.system()
                if system == "Windows":
                    _launch_windows_app(target)
                elif system == "Darwin":
                    subprocess.Popen(["open", "-a", target], stdin=subprocess.DEVNULL)
                else:
                    subprocess.Popen(
                        [target],
                        shell=True,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

            response_text = f"Right away, Sir. I have opened {name} for you."
            yield response_text
            ChatService.save_message(session_id, "assistant", response_text)

        except Exception as e:
            print(f"Action Execution Error: {e}")
            err_msg = "I encountered an error trying to execute that action, Sir."
            yield err_msg
            ChatService.save_message(session_id, "assistant", err_msg)
