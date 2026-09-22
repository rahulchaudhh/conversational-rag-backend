import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, time

from app.services.llm_service import LLMService, BOOKING_TOOL, LLMResponse
from app.schemas.booking import BookingCreate
from app.services.booking_service import BookingService
from app.db.database import Base, engine, SessionLocal
from app.db.models import Booking


def test_booking_tool_schema():
    """Verify BOOKING_TOOL adheres to Anthropic tool schema conventions."""
    assert BOOKING_TOOL["name"] == "book_interview"
    assert "description" in BOOKING_TOOL
    schema = BOOKING_TOOL["input_schema"]
    assert schema["type"] == "object"
    assert set(schema["required"]) == {"name", "email", "interview_date", "interview_time"}
    assert "name" in schema["properties"]
    assert "email" in schema["properties"]
    assert "interview_date" in schema["properties"]
    assert "interview_time" in schema["properties"]


def test_llm_response_dataclass():
    """Test LLMResponse unpacks nicely and supports string conversion."""
    res = LLMResponse(
        text="Hello world",
        tool_calls=[{"name": "book_interview", "input": {"name": "Test"}}]
    )
    assert str(res) == "Hello world"
    text, tool_calls = res
    assert text == "Hello world"
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "book_interview"


@pytest.mark.anyio
async def test_rewrite_query_empty_history():
    """When history is empty, rewrite_query returns the original message without calling API."""
    service = LLMService()
    message = "What are the core capabilities?"
    rewritten = await service.rewrite_query(message, [])
    assert rewritten == message


@pytest.mark.anyio
async def test_rewrite_query_with_history():
    """When history is present, rewrite_query invokes Claude and returns the rewritten query."""
    service = LLMService()
    mock_content = MagicMock()
    mock_content.text = "What are the security compliance rules of Acme Corp?"
    
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    
    with patch.object(service.client.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        history = [
            {"role": "user", "content": "Tell me about Acme Corp."},
            {"role": "assistant", "content": "Acme Corp is a technology provider with ISO compliance."},
        ]
        result = await service.rewrite_query("What are its security compliance rules?", history)
        
        assert result == "What are the security compliance rules of Acme Corp?"
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert "Acme Corp" in call_kwargs["messages"][0]["content"]


def test_booking_persistence_from_tool_call():
    """Verify tool call inputs properly create and save a database booking."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        tool_input = {
            "name": "Alex Mercer",
            "email": "alex.mercer@example.com",
            "interview_date": "2026-10-15",
            "interview_time": "11:30",
        }
        booking_data = BookingCreate(**tool_input)
        record = BookingService.create_booking(db, booking_data)

        assert record.id is not None
        assert record.name == "Alex Mercer"
        assert record.email == "alex.mercer@example.com"
        assert record.interview_date == date(2026, 10, 15)
        assert record.interview_time == time(11, 30)

        # Retrieve from DB to verify persistence
        saved = db.query(Booking).filter(Booking.id == record.id).first()
        assert saved is not None
        assert saved.email == "alex.mercer@example.com"
    finally:
        db.close()
