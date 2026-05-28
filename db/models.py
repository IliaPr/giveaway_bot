from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from db.base import BaseModel
from db.db_config import Base


class ParticipantModel(Base, BaseModel):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    gsheets_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    gsheets_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    raffle_result: Mapped["RaffleResultModel | None"] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        uselist=False,
    )


class RaffleResultModel(Base):
    __tablename__ = "raffle_results"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    prize_code: Mapped[str] = mapped_column(String(100))
    prize_title: Mapped[str] = mapped_column(String(255))
    prize_order: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    participant: Mapped[ParticipantModel] = relationship(
        back_populates="raffle_result")


class AppMetaModel(Base):
    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
