from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    chunking_strategy: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    total_chunks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    interview_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    interview_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )