# 🌌 J.A.R.V.I.S. (Spatial Edition)

> "Systems online. Activity panels and web processors engaged. How can I help you today, Sir?"

**J.A.R.V.I.S.** is a high-fidelity, spatial AI assistant designed for a premium, immersive experience. Built with a focus on luxury aesthetics and cognitive intelligence, it combines a stunning 3D WebGL interface with a multi-modal AI core capable of vision, real-time search, and neural text-to-speech.

![JARVIS Preview](https://img.shields.io/badge/Interface-3D_WebGL-00f0ff?style=for-the-badge)
![AI Stack](https://img.shields.io/badge/AI_Core-Groq_%2B_LangChain-f3f3f3?style=for-the-badge)
![Edge TTS](https://img.shields.io/badge/Speech-Neural_TTS-ff00ff?style=for-the-badge)

---

## ✨ Key Features

### 💎 Elite Visual Experience
- **Fluid 3D Interface**: A pulsating WebGL orb (Carbon-style) that reacts to system states.
- **Glassmorphic Design**: A premium, translucent UI with blur effects and vibrant cyan accents.
- **Responsive Workspace**: Adjustable side panels for recent activity and live web streams.

### 🧠 Cognitive Capabilities
- **Multi-Modal Intelligence**: Seamlessly switch between **Jarvis** (General), **Realtime** (Search-enabled), and **Vision** modes.
- **Real-Time Web Integration**: Integrated web processors for up-to-the-minute information retrieval.
- **Vision & Imaging**: Capture images via the built-in camera interface or upload them for instant AI analysis.
- **Neural Text-to-Speech**: High-quality, natural-sounding voices with automated "thinking" audio cues.

### 🔒 Enterprise Logic
- **Memory & RAG**: Vector-based semantic search for long-term project context.
- **LAN Security**: Token-based authentication for secure access across your local network.
- **Session Persistence**: Complete conversation history tracking with session management.

---

## 🚀 Tech Stack

### Frontend
- **Engine**: Vanilla JavaScript + WebGL
- **Styling**: Modern CSS3 (Glassmorphism, Flexbox, Variable-driven)
- **Visuals**: Three.js / Custom Orb.js
- **Typography**: Poppins (Google Fonts)

### Backend
- **Framework**: FastAPI (Python 3.13+)
- **AI Orchestration**: LangChain, LangChain-Groq
- **Vector Store**: FAISS (for high-speed semantic retrieval)
- **Speech**: Microsoft Edge TTS (Neural Engines)
- **Services**: Groq (LLM), Tavily (Search), Pollinations (Creative Imaging)

---

## 🛠️ Setup & Installation

### 1. Prerequisites
- Python 3.13+
- A [Groq API Key](https://console.groq.com/)
- A [Tavily API Key](https://tavily.com/) (Optional, for search)

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
JARVIS_AUTH_TOKEN=your_secure_token
TTS_VOICE=en-GB-RyanNeural
```

### 3. Installation
Using `uv` (recommended) or `pip`:
```bash
# Install dependencies
pip install -r requirements.txt

# Run the system
python run.py
```

---

## 📂 Project Structure

```text
JARVIS/
├── app/                # Cognitive Backend
│   ├── services/       # AI & Task Modules
│   ├── utils/          # Key Rotation & Helpers
│   └── main.py         # FastAPI Core
├── frontend/           # Visual Interface
│   ├── orb.js          # WebGL Orb Logic
│   ├── script.js       # Main UI Controller
│   └── style.css       # Premium Styling
├── run.py              # Application Entry Point
└── config.py           # Global Configuration
```

---

## 🎨 Design Philosophy
J.A.R.V.I.S. is built on the principle of **"Invisible Technology."** The interface should feel like an extension of the user's workspace—elegant, non-intrusive, yet incredibly powerful when engaged. The use of vibrant cyan (\#00f0ff) against a deep navy/black backdrop mirrors the classic aesthetic of high-end holographic interfaces.

---

*“Sir, I’ve uploaded the schematics. Ready to begin?”*
---
*Built with ❤️ and AI*
