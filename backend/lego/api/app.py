"""Local FastAPI entry point for LEGO AI Agent."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from lego import APP_NAME, __version__
from lego.agent.llm import OllamaError, chat
from lego.agent.prompts import CHAT_SYSTEM_PROMPT

app = FastAPI(title=APP_NAME, version=__version__)


class ChatRequest(BaseModel):
    """One bounded plain-text user message for a local model request."""

    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def strip_and_check_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank.")
        return value


class ChatResponse(BaseModel):
    """Plain-text response from the configured local Ollama model."""

    reply: str


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report that the local backend process is responding."""
    return {"status": "ok", "app": APP_NAME, "version": __version__}


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Send one user message to the configured local Ollama model."""
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "user", "content": request.message},
    ]
    try:
        reply = await chat(messages)
    except OllamaError as exc:
        raise HTTPException(
            status_code=503,
            detail="The local Ollama request failed. Check that Ollama is running.",
        ) from exc

    return ChatResponse(reply=reply)
