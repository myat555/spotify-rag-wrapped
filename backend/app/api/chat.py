from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.rag.chat import stream_answer

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


@router.post("")
def chat(payload: ChatRequest) -> StreamingResponse:
    return StreamingResponse(stream_answer(payload.question), media_type="text/plain")
