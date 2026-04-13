const isPreviewEnv =
    window.location.hostname.includes('usercontent') || window.location.protocol === 'blob:';
const BASE_URL = isPreviewEnv ? 'http://127.0.0.1:8000' : '';

let sessionId = null;
let currentMode = 'jarvis';
let currentVoice = localStorage.getItem('jarvis-voice') || 'en-GB-RyanNeural';
let ttsEnabled = true;
let prefThinkingEffect = true;
let prebufferedThinking = null;

let pendingImageBase64 = null;
let pendingImageMime = 'image/jpeg';
let silenceTimer = null;
let isSending = false;

const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const ttsToggle = document.getElementById('tts-toggle');
const micBtn = document.getElementById('mic-btn');
const activityContent = document.getElementById('activity-content');
const searchContent = document.getElementById('search-content');
const newChatBtn = document.getElementById('new-chat-btn');
const attachBtn = document.getElementById('attach-btn');
const cameraBtn = document.getElementById('camera-btn');
const fileInput = document.getElementById('file-input');
const attachPreview = document.getElementById('attach-preview');
const cameraModal = document.getElementById('camera-modal');
const cameraVideo = document.getElementById('camera-video');
const cameraClose = document.getElementById('camera-close');
const cameraCapture = document.getElementById('camera-capture');
let cameraStream = null;

async function bufferNextThinkingAudio() {
    try {
        const res = await fetch(`${BASE_URL}/api/thinking`);
        prebufferedThinking = await res.json();
    } catch (e) {
        console.log('Mocking Thinking Audio in Preview Env');
        prebufferedThinking = { phrase: 'Thinking...', audio: null };
    }
}
bufferNextThinkingAudio();

async function loadVoices() {
    const voiceSelect = document.getElementById('voice-select');
    if (!voiceSelect) return;
    try {
        const res = await fetch(`${BASE_URL}/api/voices`);
        const voices = await res.json();
        voiceSelect.innerHTML = '';
        voices.forEach((v) => {
            const opt = document.createElement('option');
            opt.value = v.id;
            opt.textContent = v.name;
            if (v.id === currentVoice) opt.selected = true;
            voiceSelect.appendChild(opt);
        });
    } catch (e) {
        console.error('Could not load voices', e);
    }
}
loadVoices();

const leftPanel = document.getElementById('left-panel');
const rightPanel = document.getElementById('right-panel');
const resizerLeft = document.getElementById('resizer-left');
const resizerRight = document.getElementById('resizer-right');

function initResizer(resizer, panel, isLeft) {
    let startX;
    let startWidth;
    resizer.addEventListener('mousedown', (e) => {
        startX = e.clientX;
        startWidth = parseInt(document.defaultView.getComputedStyle(panel).width, 10);
        document.documentElement.addEventListener('mousemove', doDrag);
        document.documentElement.addEventListener('mouseup', stopDrag);
        resizer.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    function doDrag(e) {
        const newWidth = isLeft
            ? startWidth + e.clientX - startX
            : startWidth - e.clientX + startX;
        if (newWidth > 200 && newWidth < 600) panel.style.width = `${newWidth}px`;
    }

    function stopDrag() {
        document.documentElement.removeEventListener('mousemove', doDrag);
        document.documentElement.removeEventListener('mouseup', stopDrag);
        resizer.classList.remove('dragging');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    }
}
initResizer(resizerLeft, leftPanel, true);
initResizer(resizerRight, rightPanel, false);

document.getElementById('open-settings').onclick = () =>
    document.getElementById('settings-modal').classList.add('active');
document.getElementById('close-settings').onclick = () =>
    document.getElementById('settings-modal').classList.remove('active');
document.getElementById('toggle-left').onchange = (e) => {
    leftPanel.classList.toggle('hidden', !e.target.checked);
    resizerLeft.classList.toggle('hidden', !e.target.checked);
};
document.getElementById('toggle-right').onchange = (e) => {
    rightPanel.classList.toggle('hidden', !e.target.checked);
    resizerRight.classList.toggle('hidden', !e.target.checked);
};
document.getElementById('toggle-thinking').onchange = (e) => {
    prefThinkingEffect = e.target.checked;
};
document.getElementById('voice-select').onchange = (e) => {
    currentVoice = e.target.value;
    localStorage.setItem('jarvis-voice', currentVoice);
};

async function loadSessions() {
    try {
        const res = await fetch(`${BASE_URL}/api/sessions`);
        const sessions = await res.json();
        activityContent.innerHTML = '';
        if (sessions.length === 0) {
            activityContent.innerHTML =
                '<div style="color: var(--text-secondary); font-size: 0.9rem; text-align: center; margin-top: 20px;">No recent sessions.</div>';
            return;
        }
        sessions.forEach((s) => {
            const div = document.createElement('div');
            div.className = 'session-item';
            const dateObj = new Date(s.timestamp);
            const dateStr = isNaN(dateObj) ? '' : dateObj.toLocaleString();
            div.innerHTML = `<div>${s.title}</div><div class="date">${dateStr}</div>`;
            div.onclick = () => loadHistory(s.id);
            activityContent.appendChild(div);
        });
    } catch (e) {
        console.log('Mocking Sessions in Preview Env');
        activityContent.innerHTML =
            '<div style="color: var(--text-secondary); font-size: 0.9rem; text-align: center; margin-top: 20px;">Preview Mode (Offline)</div>';
    }
}

async function loadHistory(id) {
    try {
        const res = await fetch(`${BASE_URL}/chat/history/${id}`);
        const data = await res.json();
        sessionId = id;
        chatContainer.innerHTML = '';
        data.messages.forEach((m) =>
            appendMessage(m.content, m.role === 'user' ? 'user-msg' : 'ai-msg')
        );
    } catch (e) {
        console.error('Could not load history', e);
    }
}

newChatBtn.onclick = () => {
    sessionId = null;
    clearPendingImage();
    chatContainer.innerHTML =
        '<div class="message ai-msg">New session started. How can I help you?</div>';
};

loadSessions();

const audioQueue = [];
let isPlaying = false;
const audioElement = new Audio();
document.body.addEventListener(
    'click',
    () => {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (Ctx) {
            const ctx = new Ctx();
            if (ctx.state === 'suspended') ctx.resume();
        }
    },
    { once: true }
);

document.querySelectorAll('.mode-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.mode-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        currentMode = btn.dataset.mode;
    });
});

ttsToggle.addEventListener('click', () => {
    ttsEnabled = !ttsEnabled;
    if (ttsEnabled) {
        ttsToggle.style.borderColor = 'var(--accent)';
        ttsToggle.style.background = 'var(--accent-glow)';
        ttsToggle.querySelector('svg').style.fill = 'var(--accent)';
    } else {
        ttsToggle.style.borderColor = 'var(--glass-border)';
        ttsToggle.style.background = 'rgba(255,255,255,0.05)';
        ttsToggle.querySelector('svg').style.fill = 'var(--text-secondary)';
        audioElement.pause();
        audioQueue.length = 0;
        isPlaying = false;
        setOrbSpeaking(false);
    }
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        micBtn.classList.add('active');
        userInput.placeholder = 'Listening... (speak now)';
    };

    recognition.onerror = (event) => {
        clearTimeout(silenceTimer);
        micBtn.classList.remove('active');
        userInput.value = '';
        userInput.placeholder = `Mic error: ${event.error}`;
    };

    recognition.onend = () => {
        clearTimeout(silenceTimer);
        micBtn.classList.remove('active');
        if (userInput.value.trim().length > 0) {
            sendMessage();
        } else {
            userInput.placeholder = 'Message Jarvis...';
        }
    };

    recognition.onresult = (e) => {
        clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => recognition.stop(), 2000);
        let transcript = '';
        for (let i = 0; i < e.results.length; i++) transcript += e.results[i][0].transcript;
        userInput.value = transcript;
        userInput.style.height = '55px';
        userInput.style.height = `${userInput.scrollHeight}px`;
    };

    micBtn.addEventListener('click', async () => {
        if (window.self !== window.top) {
            alert(
                'Voice Input Blocked by Browser Security!\n\nOpen http://localhost:8000 directly in a tab.'
            );
            return;
        }

        if (micBtn.classList.contains('active')) {
            recognition.stop();
        } else {
            userInput.value = '';
            userInput.style.height = '55px';
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach((track) => track.stop());
                recognition.start();
            } catch (err) {
                console.error('Mic Access Error:', err);
                userInput.placeholder = 'Microphone blocked or not found.';
            }
        }
    });
} else {
    micBtn.addEventListener('click', () => {
        alert('Voice input is not supported in this browser. Try Chrome or Edge.');
    });
}

function clearPendingImage() {
    pendingImageBase64 = null;
    pendingImageMime = 'image/jpeg';
    if (attachPreview) {
        attachPreview.textContent = '';
        attachPreview.style.display = 'none';
    }
}

function setPendingImageFromDataUrl(dataUrl) {
    const m = dataUrl.match(/^data:([^;]+);base64,(.+)$/);
    if (m) {
        pendingImageMime = m[1] || 'image/jpeg';
        pendingImageBase64 = m[2];
    } else {
        pendingImageMime = 'image/jpeg';
        pendingImageBase64 = dataUrl;
    }
    if (attachPreview) {
        attachPreview.textContent = 'Image ready to send';
        attachPreview.style.display = 'block';
    }
}

if (attachBtn && fileInput) {
    attachBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        const f = fileInput.files && fileInput.files[0];
        if (!f || !f.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = () => {
            if (typeof reader.result === 'string') setPendingImageFromDataUrl(reader.result);
        };
        reader.readAsDataURL(f);
        fileInput.value = '';
    });
}

async function openCamera() {
    cameraModal.classList.add('active');
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' },
            audio: false,
        });
        cameraVideo.srcObject = cameraStream;
        await cameraVideo.play();
    } catch (e) {
        console.error(e);
        alert('Could not access camera.');
        closeCamera();
    }
}

function closeCamera() {
    cameraModal.classList.remove('active');
    if (cameraStream) {
        cameraStream.getTracks().forEach((t) => t.stop());
        cameraStream = null;
    }
    cameraVideo.srcObject = null;
}

if (cameraBtn) {
    cameraBtn.addEventListener('click', () => {
        if (window.self !== window.top) {
            alert('Open http://localhost:8000 in a top-level tab to use the camera.');
            return;
        }
        openCamera();
    });
}
if (cameraClose) cameraClose.addEventListener('click', closeCamera);
if (cameraCapture) {
    cameraCapture.addEventListener('click', () => {
        const canvas = document.createElement('canvas');
        canvas.width = cameraVideo.videoWidth;
        canvas.height = cameraVideo.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(cameraVideo, 0, 0);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
        setPendingImageFromDataUrl(dataUrl);
        closeCamera();
    });
}

userInput.addEventListener('input', function () {
    this.style.height = '55px';
    this.style.height = `${this.scrollHeight}px`;
});
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (userInput.value.trim().length > 0 || pendingImageBase64) {
            sendMessage();
        }
    }
});

sendBtn.addEventListener('click', () => {
    if (userInput.value.trim().length > 0 || pendingImageBase64) {
        sendMessage();
    }
});

function setOrbSpeaking(status) {
    if (window.JarvisOrb && typeof window.JarvisOrb.setSpeaking === 'function') {
        window.JarvisOrb.setSpeaking(status);
    }
}

/** Render assistant markdown (fenced code, lists, GFM) safely for the chat bubble. */
function renderAssistantHtml(raw) {
    const text = raw || '';
    if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
        const html = marked.parse(text, { breaks: true, gfm: true });
        return DOMPurify.sanitize(html);
    }
    const esc = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    return `<div class="md-fallback">${esc.replace(/\n/g, '<br/>')}</div>`;
}

function finalizeAssistantBubble(bubble, raw) {
    bubble.classList.add('markdown-body');
    bubble.innerHTML = renderAssistantHtml(raw);
}

async function sendMessage() {
    if (isSending) return;
    isSending = true;
    const text = userInput.value.trim();
    if (!text && !pendingImageBase64) return;

    const displayText = text || (pendingImageBase64 ? '[Image]' : '');
    userInput.value = '';
    userInput.style.height = '55px';
    appendMessage(displayText, 'user-msg');

    const body = {
        message: text || (pendingImageBase64 ? 'Please describe this image.' : ''),
        session_id: sessionId,
        tts: ttsEnabled,
        voice: currentVoice,
    };
    if (pendingImageBase64) {
        body.image_base64 = pendingImageBase64;
        body.image_mime = pendingImageMime;
    }
    clearPendingImage();

    let thinkingBubble = null;
    if (prefThinkingEffect && prebufferedThinking) {
        thinkingBubble = document.createElement('div');
        thinkingBubble.className = 'message ai-msg thinking-msg';
        thinkingBubble.textContent = prebufferedThinking.phrase;
        chatContainer.appendChild(thinkingBubble);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        if (ttsEnabled && prebufferedThinking.audio) {
            audioQueue.push(prebufferedThinking.audio);
            playNextAudio();
        }
        bufferNextThinkingAudio();
    }

    const aiBubble = createAiBubble();
    const streamSpan = document.createElement('span');
    streamSpan.className = 'ai-stream';
    const cursor = document.createElement('span');
    cursor.className = 'cursor';
    aiBubble.appendChild(streamSpan);
    aiBubble.appendChild(cursor);

    let assistantPlain = '';
    let genImageWrap = null;

    try {
        const response = await fetch(`${BASE_URL}/chat/${currentMode}/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) throw new Error('Network response was not ok');

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buf = '';
        let firstChunkReceived = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                loadSessions();
                break;
            }

            buf += decoder.decode(value, { stream: true });
            const parts = buf.split('\n\n');
            buf = parts.pop();

            for (const part of parts) {
                if (part.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(part.slice(6));

                        if (!firstChunkReceived) {
                            if (thinkingBubble) thinkingBubble.remove();
                            firstChunkReceived = true;
                        }

                        if (data.session_id) sessionId = data.session_id;

                        if (data.search_results) {
                            searchContent.innerHTML = '';
                            data.search_results.forEach((res) => {
                                const card = document.createElement('div');
                                card.className = 'search-card';
                                card.innerHTML = `<a href="${res.url}" target="_blank">${res.title}</a><p>${res.content}</p>`;
                                searchContent.appendChild(card);
                            });
                        }

                        if (data.image && (data.image.prompt || data.image.url)) {
                            if (!genImageWrap) {
                                genImageWrap = document.createElement('div');
                                genImageWrap.className = 'gen-image-wrap';
                                aiBubble.parentNode.insertBefore(genImageWrap, aiBubble);
                            }
                            genImageWrap.innerHTML = '';
                            const img = document.createElement('img');
                            img.alt = 'Generated image';
                            img.referrerPolicy = 'no-referrer';
                            img.loading = 'lazy';
                            img.className = 'gen-image-img';
                            const direct = data.image.url || '';
                            const p = data.image.prompt || '';
                            img.src = p
                                ? `${BASE_URL}/api/pollinations-image?prompt=${encodeURIComponent(p)}`
                                : direct;
                            img.onerror = () => {
                                genImageWrap.innerHTML = '';
                                const link = document.createElement('a');
                                link.href = direct || img.src;
                                link.target = '_blank';
                                link.rel = 'noopener noreferrer';
                                link.className = 'gen-image-fallback';
                                link.textContent = 'Open generated image (direct link)';
                                genImageWrap.appendChild(link);
                            };
                            genImageWrap.appendChild(img);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }

                        if (data.action) {
                            const actionDiv = document.createElement('div');
                            actionDiv.className = 'action-badge';
                            actionDiv.innerHTML = `<svg style="width:16px;height:16px;fill:var(--accent)" viewBox="0 0 24 24"><path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.06-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.73,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.06,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.43-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.49-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/></svg>
                                    Executing Action: Opening ${data.action.name}`;
                            aiBubble.parentNode.insertBefore(actionDiv, aiBubble);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }

                        if (data.chunk) {
                            assistantPlain += data.chunk;
                            streamSpan.textContent = assistantPlain;
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }

                        if (data.audio && ttsEnabled) {
                            audioQueue.push(data.audio);
                            playNextAudio();
                        }
                        if (data.done) {
                            isSending = false;
                            cursor.remove();
                            streamSpan.remove();
                            finalizeAssistantBubble(aiBubble, assistantPlain);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }

        // Handle error events from groq_service
        if (data.error) {
            if (data.error === 'rate_limit') {
                addMessage(`⚠️ ${data.message}`, 'ai-msg error-msg');
            } else {
                addMessage(`⚠️ Error: ${data.message}`, 'ai-msg error-msg');
            }
            return;
        }
    } catch (error) {
        isSending = false;
        if (thinkingBubble) thinkingBubble.remove();
        streamSpan.remove();
        console.warn('Backend not reachable.', error);
        const mockText =
            'Sir, my connection to the primary servers has been interrupted. Please ensure the backend is running locally on port 8000.';
        let i = 0;
        const streamInterval = setInterval(() => {
            if (i < mockText.length) {
                aiBubble.insertBefore(document.createTextNode(mockText.charAt(i)), cursor);
                chatContainer.scrollTop = chatContainer.scrollHeight;
                i++;
            } else {
                clearInterval(streamInterval);
                cursor.remove();
                finalizeAssistantBubble(aiBubble, mockText);
            }
        }, 25);
    }
}

function appendMessage(text, className) {
    const div = document.createElement('div');
    div.className = `message ${className}`;
    if (className === 'ai-msg') {
        finalizeAssistantBubble(div, text);
    } else {
        div.textContent = text;
    }
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function createAiBubble() {
    const div = document.createElement('div');
    div.className = 'message ai-msg';
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return div;
}

function playNextAudio() {
    if (isPlaying || audioQueue.length === 0) return;
    isPlaying = true;
    setOrbSpeaking(true);
    const b64 = audioQueue.shift();
    audioElement.src = `data:audio/mp3;base64,${b64}`;
    audioElement.play().catch(() => {
        isPlaying = false;
        setOrbSpeaking(false);
        playNextAudio();
    });
    audioElement.onended = () => {
        isPlaying = false;
        if (audioQueue.length === 0) setOrbSpeaking(false);
        else playNextAudio();
    };
}
