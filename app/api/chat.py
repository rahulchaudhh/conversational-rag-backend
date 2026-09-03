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
Answer the user's questions accurately, clearly, and concisely using the provided document context.

Guidelines:
- For greetings (e.g., "hi", "hello", "hey"): greet the user warmly, give a brief 1-2 sentence overview of what you can assist with based on the provided document context, and mention they can ask questions or schedule an interview.
- For specific questions: answer using the context. If the information is not available, politely state that the answer is not mentioned in the provided documents.
- Maintain a natural, conversational tone with clear formatting and bullet points where helpful.
- Current year context: The current year is 2026. Accept 2026 dates as current and valid.

If the user wants to schedule or book an interview, politely ask for their full name, email, preferred date (YYYY-MM-DD), and time (HH:MM).
ONCE the user has provided ALL four details, you MUST include a JSON block formatted exactly like this:
<booking>
{{"name": "Full Name", "email": "email@example.com", "interview_date": "YYYY-MM-DD", "interview_time": "HH:MM"}}
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
            reply += f"\n\n✅ Interview successfully booked! (Booking ID: {booking_record.id})"
            
        except (json.JSONDecodeError, ValidationError):
            reply = "I noticed you want to book an interview, but some details were missing or invalid. Please ensure you provide your full name, email, date (YYYY-MM-DD), and time (HH:MM)."

    # 6. Save current turn to Redis Memory
    redis_memory.add_message(request.session_id, "user", request.message)
    redis_memory.add_message(request.session_id, "assistant", reply)

    return ChatResponse(
        session_id=request.session_id,
        reply=reply
    )