from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    message: str = Field("", description="User message text")
    session_id: Optional[str] = None
    tts: bool = False
    image_base64: Optional[str] = Field(
        None, description="Optional raw or data-URL base64 image for vision"
    )
    image_mime: Optional[str] = Field("image/jpeg", description="MIME type of the image")
    voice: Optional[str] = Field(None, description="Optional Edge-TTS voice override")

    @model_validator(mode="after")
    def message_or_image(self):
        has_text = bool(self.message and self.message.strip())
        if not has_text and not self.image_base64:
            raise ValueError("Provide a non-empty message and/or an image.")
        return self


class ChatResponse(BaseModel):
    response: str
    session_id: str


class TtsRequest(BaseModel):
    text: str
    voice: Optional[str] = None


class TtsResponse(BaseModel):
    audio_base64: str
    format: str = "mp3"


class HealthResponse(BaseModel):
    status: str
    groq_configured: bool
    tavily_configured: bool
    vector_chunks: int
