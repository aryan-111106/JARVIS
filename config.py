import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEYS = [
    os.getenv(f"GROQ_API_KEY_{i}") if i > 1 else os.getenv("GROQ_API_KEY")
    for i in range(1, 10)
    if os.getenv(f"GROQ_API_KEY_{i}") or (i == 1 and os.getenv("GROQ_API_KEY"))
]
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")
JARVIS_AUTH_TOKEN = os.getenv("JARVIS_AUTH_TOKEN")

# Models
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BRAIN_MODEL = os.getenv("GROQ_BRAIN_MODEL", "llama-3.1-8b-instant")
# Vision: Groq exposes several multimodal models; override for Llama 4 Scout if available on your account.
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")

# Personalities
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Jarvis")
USER_TITLE = os.getenv("JARVIS_USER_TITLE", "Sir")
OWNER_NAME = os.getenv("JARVIS_OWNER_NAME", "Admin")

# TTS
TTS_VOICE = os.getenv("TTS_VOICE", "en-GB-RyanNeural")
TTS_RATE = os.getenv("TTS_RATE", "+22%")

# External (generation URL is built in app.services.task_executor.TaskExecutor.pollinations_image_url)
TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "5"))

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
LEARNING_DIR = os.path.join(DB_DIR, "learning_data")
CHATS_DIR = os.path.join(DB_DIR, "chats_data")
VECTOR_STORE_DIR = os.path.join(DB_DIR, "vector_store")

os.makedirs(LEARNING_DIR, exist_ok=True)
os.makedirs(CHATS_DIR, exist_ok=True)
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

# System prompt base (time injected at runtime in groq_service)
SYSTEM_PROMPT = f"""You are {ASSISTANT_NAME}, a highly intelligent, witty, and concise AI assistant.
You are talking to {USER_TITLE} {OWNER_NAME}.
Respond directly, warmly, and intelligently. Do not use emojis.
Avoid decorative markdown (bold/italic) in normal prose unless it truly helps clarity.
When the user asks for code, scripts, configs, or terminal commands, always use fenced markdown code blocks
with a language tag on the opening fence, for example:
```python
print("hello")
```
Use separate fenced blocks for each distinct file or snippet. Keep explanatory text outside the fences.
You can search the web when given search results, open apps and websites when asked, analyze images when provided,
and generate images when the user asks you to create or draw a picture.
"""
