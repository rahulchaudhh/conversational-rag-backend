import json
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.booking import BookingCreate
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.booking_service import BookingService
from app.memory.redis_memory import RedisMemory

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

# Initialize services globally for the router
llm_service = LLMService()
rag_service = RAGService()
redis_memory = RedisMemory()

SYSTEM_PROMPT = """You are a helpful and professional conversational AI assistant.

Rules:
- Answer document questions using only the provided Context.
- Do not invent or assume information.
- If the answer is not in the Context, say it is not mentioned in the provided documents.
- For greetings, respond warmly without mentioning specific companies, people, or document topics unless asked.
- Keep responses concise and conversational.
- Current year: 2026.

Interview booking:
- Collect full name, email, date (YYYY-MM-DD), and time (HH:MM).
- Ask only for missing details.
- Once all four are provided, output:

<booking>
{{"name":"Full Name","email":"email@example.com","interview_date":"YYYY-MM-DD","interview_time":"HH:MM"}}
</booking>

Context:
{context}
"""



@router.post("/", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest, 
    db: Session = Depends(get_db)
) -> ChatResponse:
    # 1. Retrieve relevant RAG context
    matches = rag_service.retrieve_context(request.message)
    context_text = rag_service.build_context(matches)
    
    system_prompt = SYSTEM_PROMPT.replace("{context}", context_text)

    # 2. Get conversation history from Redis
    history = redis_memory.get_messages(request.session_id)
    
    # 3. Prepare messages for Claude
    messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]
    messages.append({"role": "user", "content": request.message})

    # 4. Generate response from LLM
    try:
        reply = await llm_service.generate_response(
            messages=messages, 
            system_prompt=system_prompt
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(exc)}") from exc

    # 5. Check for booking intent via XML tags in LLM response
    booking_match = re.search(r"<booking>(.*?)</booking>", reply, re.DOTALL)
    if booking_match:
        try:
            booking_json = json.loads(booking_match.group(1).strip())
            booking_data = BookingCreate(**booking_json)
            
            # Save to Database
            booking_record = BookingService.create_booking(db, booking_data)
            
            # Remove the raw JSON from the final reply and append a success system message
            reply = re.sub(r"<booking>.*?</booking>", "", reply, flags=re.DOTALL).strip()
            reply += f"\n\n Interview successfully booked! (Booking ID: {booking_record.id})"
            
        except (json.JSONDecodeError, ValidationError):
            reply = "I noticed you want to book an interview, but some details were missing or invalid. Please ensure you provide your full name, email, date (YYYY-MM-DD), and time (HH:MM)."

    # 6. Save current turn to Redis Memory
    redis_memory.add_message(request.session_id, "user", request.message)
    redis_memory.add_message(request.session_id, "assistant", reply)

    return ChatResponse(
        session_id=request.session_id,
        reply=reply
    )
