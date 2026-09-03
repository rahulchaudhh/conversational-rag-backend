from datetime import date, time
from pydantic import BaseModel, EmailStr, Field

class BookingCreate(BaseModel):
    """Schema for creating a new interview booking extracted by the LLM."""
    name: str = Field(..., description="Full name of the candidate.")
    email: EmailStr = Field(..., description="Email address of the candidate.")
    interview_date: date = Field(..., description="Date of the interview (YYYY-MM-DD).")
    interview_time: time = Field(..., description="Time of the interview (HH:MM).")

class BookingResponse(BaseModel):
    """Schema for returning booking confirmation."""
    booking_id: int
    name: str
    email: str
    interview_date: date
    interview_time: time
    message: str = "Interview booked successfully."