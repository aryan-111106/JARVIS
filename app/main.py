import asyncio
import base64
import concurrent.futures
import json
import os
import random
import re
from typing import AsyncIterator, Optional

import httpx
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import TTS_RATE, TTS_VOICE

from app.models import ChatRequest, ChatResponse, HealthResponse, TtsRequest, TtsResponse
from app.services.brain_service import BrainService
from app.services.chat_service import ChatService
from app.services.groq_service import GroqService
from app.services.realtime_service import RealtimeService
from app.services.task_executor import TaskExecutor
from app.services.vector_store import vector_store
from app.services.vision_service import VisionService
from app.utils.key_rotation import key_manager

try:
    import edge_tts
except ImportError:
    edge_tts = None

app = FastAPI(title="J.A.R.V.I.S. API")

@app.middleware("http")
async def lan_auth_middleware(request: Request, call_next):
    from config import JARVIS_AUTH_TOKEN
    if JARVIS_AUTH_TOKEN:
        host = request.client.host
        # Only enforce if not localhost/127.0.0.1
        if host not in ("127.0.0.1", "localhost", "::1"):
            token = request.headers.get("X-Jarvis-Token") or request.headers.get("Authorization")
            if token:
                if token.startswith("Bearer "):
                    token = token[7:]
                if token != JARVIS_AUTH_TOKEN:
                    return JSONResponse({"detail": "Unauthorized Sir. Invalid token."}, status_code=401)
            else:
                return JSONResponse({"detail": "Unauthorized Sir. Token required for LAN access."}, status_code=401)
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

tts_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def generate_audio_sync(text: str, voice: Optional[str] = None) -> str:
    if not edge_tts:
        return ""
    try:
        selected_voice = voice or TTS_VOICE
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        communicate = edge_tts.Communicate(text, selected_voice, rate=TTS_RATE)

        import tempfile

        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        loop.run_until_complete(communicate.save(path))
        loop.close()

        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        os.remove(path)
        return b64
    except Exception as e:
        print(f"TTS Error: {e}")
        return ""


THINKING_PHRASES = [
    "Just a moment, Sir.",
    "Let me check that for you.",
    "One second, please.",
    "Processing your request.",
    "I'm on it.",
]
PREGENERATED_THINKING: list = []


@app.on_event("startup")
def preload_thinking_audio():
    if not edge_tts:
        return
    print("Pre-generating Neural Thinking Audio... (this takes a few seconds)")
    for phrase in THINKING_PHRASES:
        b64 = generate_audio_sync(phrase)
        if b64:
            PREGENERATED_THINKING.append({"phrase": phrase, "audio": b64})


@app.get("/api/thinking")
async def get_thinking_audio():
    if PREGENERATED_THINKING:
        return JSONResponse(random.choice(PREGENERATED_THINKING))
    return JSONResponse({"phrase": "Processing...", "audio": ""})


async def sse_generator(
    generator: AsyncIterator[str], session_id: str, enable_tts: bool, voice: Optional[str] = None
):
    yield f"data: {json.dumps({'session_id': session_id, 'chunk': '', 'done': False})}\n\n"

    buffer = ""
    futures = []
    sentence_end_pattern = re.compile(r"(?<=[.!?])\s+")
    code_block_pattern = re.compile(r"```[\s\S]*?```|`[^`]*`")

    try:
        async for chunk in generator:
            if chunk.startswith("__SEARCH_RESULTS__:"):
                search_data = chunk.replace("__SEARCH_RESULTS__:", "")
                yield f"data: {json.dumps({'search_results': json.loads(search_data)})}\n\n"
                continue

            if chunk.startswith("__ACTION__:"):
                action_data = chunk.replace("__ACTION__:", "")
                yield f"data: {json.dumps({'action': json.loads(action_data)})}\n\n"
                continue

            if chunk.startswith("__IMAGE__:"):
                image_data = chunk.replace("__IMAGE__:", "")
                yield f"data: {json.dumps({'image': json.loads(image_data)})}\n\n"
                continue

            yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"

            if enable_tts:
                buffer += chunk
                splits = sentence_end_pattern.split(buffer)

                if len(splits) > 1:
                    sentence = splits[0].strip()
                    buffer = "".join(splits[1:])

                    sentence_for_tts = code_block_pattern.sub("", sentence).strip()
                    if sentence_for_tts and len(sentence_for_tts) > 2:
                        future = asyncio.get_event_loop().run_in_executor(
                            tts_executor, generate_audio_sync, sentence_for_tts, voice
                        )
                        futures.append((sentence, future))

            if enable_tts:
                while futures and futures[0][1].done():
                    sent, fut = futures.pop(0)
                    try:
                        b64_audio = fut.result(timeout=1.0)
                        if b64_audio:
                            yield f"data: {json.dumps({'audio': b64_audio, 'sentence': sent})}\n\n"
                    except Exception:
                        pass

        if enable_tts and buffer.strip() and len(buffer.strip()) > 2:
            buffer_for_tts = code_block_pattern.sub("", buffer.strip()).strip()
            if buffer_for_tts:
                future = asyncio.get_event_loop().run_in_executor(
                    tts_executor, generate_audio_sync, buffer_for_tts, voice
                )
                futures.append((buffer_for_tts, future))

        if enable_tts:
            for sent, fut in futures:
                try:
                    b64_audio = await asyncio.wrap_future(fut)
                    if b64_audio:
                        yield f"data: {json.dumps({'audio': b64_audio, 'sentence': sent})}\n\n"
                except Exception:
                    pass

        yield f"data: {json.dumps({'chunk': '', 'done': True, 'session_id': session_id})}\n\n"

    except Exception as e:
        print(f"Stream Error: {e}")
        yield f"data: {json.dumps({'chunk': '\\n[System Error]', 'done': True})}\n\n"


async def jarvis_stream_core(req: ChatRequest, session_id: str) -> AsyncIterator[str]:
    brain_key, chat_key = key_manager.get_keys()

    if req.image_base64:
        async for part in VisionService.stream_vision(
            req.message,
            req.image_base64,
            req.image_mime or "image/jpeg",
            session_id,
            chat_key,
        ):
            yield part
        return

    intent = await BrainService.classify_intent(req.message, brain_key)
    print(f"JARVIS Intent: {intent} | Message: {req.message}")

    if intent == "image_gen":
        async for part in TaskExecutor.stream_image_generation(
            req.message, session_id, brain_key
        ):
            yield part
    elif intent == "action":
        async for part in TaskExecutor.stream_action(req.message, session_id, brain_key):
            yield part
    elif intent == "realtime":
        async for part in RealtimeService.stream_realtime(
            req.message, session_id, chat_key
        ):
            yield part
    else:
        async for part in GroqService.stream_general(
            req.message, session_id, chat_key
        ):
            yield part


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    session_id = ChatService.get_or_create_session(req.session_id)
    _, chat_key = key_manager.get_keys()
    if req.image_base64:
        gen = VisionService.stream_vision(
            req.message,
            req.image_base64,
            req.image_mime or "image/jpeg",
            session_id,
            chat_key,
        )
    else:
        gen = GroqService.stream_general(req.message, session_id, chat_key)
    return StreamingResponse(
        sse_generator(gen, session_id, req.tts, req.voice), media_type="text/event-stream"
    )


@app.post("/chat/jarvis/stream")
async def chat_jarvis_stream(req: ChatRequest):
    session_id = ChatService.get_or_create_session(req.session_id)
    gen = jarvis_stream_core(req, session_id)
    return StreamingResponse(
        sse_generator(gen, session_id, req.tts, req.voice), media_type="text/event-stream"
    )


@app.post("/chat/general/stream")
async def chat_general_stream(req: ChatRequest):
    session_id = ChatService.get_or_create_session(req.session_id)
    _, chat_key = key_manager.get_keys()
    if req.image_base64:
        gen = VisionService.stream_vision(
            req.message,
            req.image_base64,
            req.image_mime or "image/jpeg",
            session_id,
            chat_key,
        )
    else:
        gen = GroqService.stream_general(req.message, session_id, chat_key)
    return StreamingResponse(
        sse_generator(gen, session_id, req.tts, req.voice), media_type="text/event-stream"
    )


@app.post("/chat/realtime/stream")
async def chat_realtime_stream(req: ChatRequest):
    session_id = ChatService.get_or_create_session(req.session_id)
    _, chat_key = key_manager.get_keys()
    if req.image_base64:
        gen = VisionService.stream_vision(
            req.message,
            req.image_base64,
            req.image_mime or "image/jpeg",
            session_id,
            chat_key,
        )
    else:
        gen = RealtimeService.stream_realtime(req.message, session_id, chat_key)
    return StreamingResponse(
        sse_generator(gen, session_id, req.tts, req.voice), media_type="text/event-stream"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_non_stream(req: ChatRequest):
    session_id = ChatService.get_or_create_session(req.session_id)
    _, chat_key = key_manager.get_keys()
    if req.image_base64:
        text = ""
        async for part in VisionService.stream_vision(
            req.message,
            req.image_base64,
            req.image_mime or "image/jpeg",
            session_id,
            chat_key,
        ):
            text += part
    else:
        text = await GroqService.invoke_general(req.message, session_id, chat_key)
    return ChatResponse(response=text, session_id=session_id)


@app.post("/chat/realtime", response_model=ChatResponse)
async def chat_realtime_non_stream(req: ChatRequest):
    session_id = ChatService.get_or_create_session(req.session_id)
    _, chat_key = key_manager.get_keys()
    if req.image_base64:
        text = ""
        async for part in VisionService.stream_vision(
            req.message,
            req.image_base64,
            req.image_mime or "image/jpeg",
            session_id,
            chat_key,
        ):
            text += part
    else:
        text = await RealtimeService.invoke_realtime(req.message, session_id, chat_key)
    return ChatResponse(response=text, session_id=session_id)


@app.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    history = ChatService.get_history(session_id)
    return JSONResponse(content={"messages": history})


@app.get("/api/sessions")
async def get_sessions():
    """List saved sessions (sidebar)."""
    return ChatService.list_sessions()


@app.post("/tts", response_model=TtsResponse)
async def tts_endpoint(body: TtsRequest):
    b64 = generate_audio_sync(body.text, body.voice)
    return TtsResponse(audio_base64=b64, format="mp3")


@app.get("/api/voices")
async def get_voices():
    """Returns a subset of popular edge-tts voices for selection."""
    return JSONResponse([
        {"id": "en-GB-RyanNeural", "name": "UK Male (Ryan)"},
        {"id": "en-GB-SoniaNeural", "name": "UK Female (Sonia)"},
        {"id": "en-US-GuyNeural", "name": "US Male (Guy)"},
        {"id": "en-US-AriaNeural", "name": "US Female (Aria)"},
        {"id": "en-AU-WilliamNeural", "name": "AU Male (William)"},
        {"id": "en-IN-PrabhatNeural", "name": "IN Male (Prabhat)"},
    ])


@app.get("/health", response_model=HealthResponse)
async def health():
    from config import GROQ_API_KEYS, TAVILY_API_KEY

    return HealthResponse(
        status="ok",
        groq_configured=bool(GROQ_API_KEYS),
        tavily_configured=bool(TAVILY_API_KEY),
        vector_chunks=len(vector_store.chunks),
    )


@app.get("/api/pollinations-image")
async def pollinations_image_proxy(
    prompt: str = Query(
        ...,
        max_length=600,
        description="Same prompt text used for generation (avoids broken direct hotlinks).",
    ),
):
    """
    Fetch the generated image from Pollinations server-side and return bytes.
    The UI uses this as <img src> so the browser does not depend on legacy domains or referrers.
    """
    from urllib.parse import unquote

    from app.services.task_executor import TaskExecutor
    from config import POLLINATIONS_API_KEY

    p = unquote(prompt).strip()
    url = TaskExecutor.pollinations_image_url(p)
    try:
        headers = {"User-Agent": "JARVIS/1.0 (pollinations-image)"}
        if POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
        r.raise_for_status()
        ct = r.headers.get("content-type", "image/jpeg")
        return Response(content=r.content, media_type=ct)
    except Exception as e:
        print(f"[pollinations-image] {url[:120]}... err={e}")
        return JSONResponse({"detail": str(e)}, status_code=502)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/")
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<p>Missing frontend/index.html</p>", status_code=500)


# Legacy paths (older UI)
@app.get("/api/history/{session_id}")
async def get_history_legacy(session_id: str):
    return await get_chat_history(session_id)
