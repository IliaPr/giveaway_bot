from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Participant(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    telegram_user_id: int
    username: str | None
    full_name: str | None = None
    phone: str | None = None
    company: str | None = None
    position: str | None = None
    created_at: datetime
    gsheets_synced_at: datetime | None
    gsheets_error: str | None


class PrizeAssignment(BaseModel):
    model_config = ConfigDict(frozen=True)

    participant_id: int
    prize_code: str
    prize_title: str
    prize_order: int


class PrizeWinner(BaseModel):
    model_config = ConfigDict(frozen=True)

    result_id: int
    participant_id: int
    telegram_user_id: int
    username: str | None
    full_name: str | None = None
    phone: str | None = None
    company: str | None = None
    position: str | None = None
    prize_code: str
    prize_title: str
    prize_order: int
    created_at: datetime
    notified_at: datetime | None
