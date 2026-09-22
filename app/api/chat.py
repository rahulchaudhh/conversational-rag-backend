import json
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db.database import get_db
from app.db.models import Booking
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.booking import BookingCreate
from app.services.llm_service import LLMService, BOOKING_TOOL
from app.services.rag_service import RAGService
from app.services.booking_service import BookingService
from app.memory.redis_memory import RedisMemory
from app.core.config import settings
from app.core.rate_limiter import RateLimiter
from app.core.dependencies import (
    get_llm_service,
    get_rag_service,
    get_redis_memory,
)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

chat_limiter = RateLimiter(times=settings.rate_limit_chat_rpm, seconds=60, key_prefix="rl_chat")

SYSTEM_PROMPT = """You are a helpful and professional conversational AI assistant.

Rules:
- Answer document questions using only the provided Context.
- Do not invent or assume information.
- If the answer is not in the Context, say it is not mentioned in the provided documents.
- For greetings, respond warmly without mentioning specific companies, people, or document topics unless asked.
- Keep responses concise and conversational.
- Current year: 2026.
Interview Booking:
- Help users schedule interviews by collecting 4 required details: full name, email, interview date (YYYY-MM-DD), and time (HH:MM).
- Ask politely only for whichever details are missing.
- When all 4 details are provided by the user, invoke the `book_interview` tool to record the appointment.

Context:
{context}
"""


@router.post("/", dependencies=[Depends(chat_limiter)])
async def chat_endpoint(
    request: ChatRequest, 
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
    redis_memory: RedisMemory = Depends(get_redis_memory),
):
    # 1. Determine if message is conversational / greeting / general inquiry
    clean_msg = re.sub(r"[^\w\s]", " ", request.message.lower()).strip()
    words = clean_msg.split()

    common_greetings = {"hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "howdy", "sup", "yo"}
    general_intents = [
        "what can you do",
        "what can you help me with",
        "how can you help",
        "how can you help me",
        "who are you",
        "what are you",
        "what is your name",
        "help me",
        "help",
        "thank you",
        "thanks",
        "bye",
        "goodbye",
    ]

    is_greeting = (
        clean_msg in common_greetings
        or any(clean_msg == gi or clean_msg.startswith(gi + " ") for gi in general_intents)
        or (len(words) <= 3 and any(w in common_greetings for w in words))
        or (any(w in common_greetings for w in words) and any(phrase in clean_msg for phrase in ["help", "how are you", "what can you"]))
    )

    # 2. Get conversation history from Redis
    history = redis_memory.get_messages(request.session_id)

    if is_greeting:
        context_text = "No document context needed for greetings or general assistant capabilities."
    else:
        # Multi-turn query reformulation: resolve references like 'it', 'its', 'that'
        search_query = request.message
        if history:
            search_query = await llm_service.rewrite_query(request.message, history)

        # Retrieve relevant RAG context for actual questions using search_query
        matches = rag_service.retrieve_context(search_query)
        context_text = rag_service.build_context(matches)
    
    system_prompt = SYSTEM_PROMPT.replace("{context}", context_text)

    # 3. Prepare messages for Claude
    messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]
    messages.append({"role": "user", "content": request.message})

    # 4. Stream response if requested
    if request.stream:
        async def event_generator():
            full_reply = ""
            tool_calls = []
            try:
                async for event_type, data in llm_service.generate_response_stream(
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=[BOOKING_TOOL],
                ):
                    if event_type == "token":
                        full_reply += data
                        yield f"data: {json.dumps({'token': data})}\n\n"
                    elif event_type == "tool_calls":
                        tool_calls = data
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"
                return

            booking_id = None
            for tool_call in tool_calls:
                if tool_call.get("name") == "book_interview":
                    try:
                        booking_data = BookingCreate(**tool_call.get("input", {}))
                        booking_record = BookingService.create_booking(db, booking_data)
                        booking_id = booking_record.id
                        yield f"data: {json.dumps({'booking': {'id': booking_record.id, 'name': booking_record.name, 'date': booking_record.interview_date.isoformat(), 'time': booking_record.interview_time.strftime('%H:%M')}})}\n\n"
                    except (ValidationError, Exception) as err:
                        import logging
                        logging.getLogger(__name__).error(f"Failed to record booking from tool call: {err}")

            cleaned_reply = full_reply.strip()
            if booking_id:
                if cleaned_reply:
                    cleaned_reply += f"\n\n✅ Interview successfully booked! (Booking ID: {booking_id})"
                else:
                    cleaned_reply = f"✅ Interview successfully booked! (Booking ID: {booking_id})"

            # Save current turn to Redis Memory
            redis_memory.add_message(request.session_id, "user", request.message)
            redis_memory.add_message(request.session_id, "assistant", cleaned_reply)

            yield f"data: {json.dumps({'event': 'done', 'session_id': request.session_id})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # 5. Non-streaming fallback
    try:
        llm_res = await llm_service.generate_response(
            messages=messages, 
            system_prompt=system_prompt,
            tools=[BOOKING_TOOL],
        )
        reply = llm_res.text
        tool_calls = llm_res.tool_calls
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(exc)}") from exc

    # Process native tool calls
    booking_id = None
    for tool_call in tool_calls:
        if tool_call.get("name") == "book_interview":
            try:
                booking_data = BookingCreate(**tool_call.get("input", {}))
                booking_record = BookingService.create_booking(db, booking_data)
                booking_id = booking_record.id
            except (ValidationError, Exception) as err:
                import logging
                logging.getLogger(__name__).error(f"Failed to record booking from tool call: {err}")

    if booking_id:
        if reply:
            reply += f"\n\n✅ Interview successfully booked! (Booking ID: {booking_id})"
        else:
            reply = f"✅ Interview successfully booked! (Booking ID: {booking_id})"

    # Save current turn to Redis Memory
    redis_memory.add_message(request.session_id, "user", request.message)
    redis_memory.add_message(request.session_id, "assistant", reply)

    return ChatResponse(
        session_id=request.session_id,
        reply=reply,
    )



@router.get("/bookings")
def get_all_bookings(db: Session = Depends(get_db)):
    """Retrieve all scheduled bookings."""
    bookings = db.query(Booking).order_by(Booking.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "email": b.email,
            "interview_date": b.interview_date.isoformat() if b.interview_date else None,
            "interview_time": b.interview_time.strftime("%H:%M") if b.interview_time else None,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in bookings
    ]


@router.get("/sessions")
def get_all_sessions(redis_memory: RedisMemory = Depends(get_redis_memory)):
    """Retrieve all active chat sessions stored in Redis."""
    try:
        sessions = redis_memory.get_all_sessions()
        return sessions
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(exc)}") from exc


@router.get("/{session_id}/history")
def get_session_history(
    session_id: str,
    redis_memory: RedisMemory = Depends(get_redis_memory),
):
    """Retrieve all messages for a session from Redis."""
    try:
        messages = redis_memory.get_messages(session_id)
        return {"session_id": session_id, "messages": messages}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(exc)}") from exc


@router.delete("/{session_id}")
def clear_session_history(
    session_id: str,
    redis_memory: RedisMemory = Depends(get_redis_memory),
):
    """Clear conversational memory for a session from Redis."""
    try:
        redis_memory.clear_session(session_id)
        return {"message": f"Session {session_id} history cleared successfully."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(exc)}") from exc
