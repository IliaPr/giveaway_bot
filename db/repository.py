from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from db.db_config import SyncSession, build_sync_engine
from db.models import AppMetaModel, ParticipantModel, RaffleResultModel
from db.schemas import Participant, PrizeAssignment, PrizeWinner


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DuplicateParticipantError(Exception):
    pass


class Repository:
    def __init__(self, database_dsn: str | None = None) -> None:
        self.database_dsn = database_dsn
        if database_dsn:
            engine = build_sync_engine(database_dsn)
            self._session_factory = sessionmaker(bind=engine)
        else:
            self._session_factory = SyncSession

    def get_participant_by_telegram_user_id(self, telegram_user_id: int) -> Participant | None:
        with self._session() as session:
            participant = session.scalar(
                select(ParticipantModel).where(
                    ParticipantModel.telegram_user_id == telegram_user_id)
            )
            return self._participant_from_model(participant)

    def create_participant(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        full_name: str,
        phone: str,
        company: str,
        position: str,
    ) -> Participant:
        with self._session() as session:
            participant = ParticipantModel(
                telegram_user_id=telegram_user_id,
                username=username,
                full_name=full_name,
                phone=phone,
                company=company,
                position=position,
            )
            session.add(participant)
            try:
                session.commit()
            except IntegrityError as error:
                session.rollback()
                raise DuplicateParticipantError from error
            session.refresh(participant)
            return Participant(
                id=participant.id,
                telegram_user_id=participant.telegram_user_id,
                username=participant.username,
                full_name=participant.full_name,
                phone=participant.phone,
                company=participant.company,
                position=participant.position,
                created_at=participant.created_at,
                gsheets_synced_at=participant.gsheets_synced_at,
                gsheets_error=participant.gsheets_error,
            )

    def get_participant_by_id(self, participant_id: int) -> Participant | None:
        with self._session() as session:
            participant = session.get(ParticipantModel, participant_id)
            return self._participant_from_model(participant)

    def mark_participant_synced(self, participant_id: int) -> None:
        with self._session() as session:
            participant = session.get(ParticipantModel, participant_id)
            if participant is None:
                return
            participant.gsheets_synced_at = utc_now()
            participant.gsheets_error = None
            session.commit()

    def mark_participant_sync_error(self, participant_id: int, error_message: str) -> None:
        with self._session() as session:
            participant = session.get(ParticipantModel, participant_id)
            if participant is None:
                return
            participant.gsheets_error = error_message[:1000]
            session.commit()

    def list_participants(self) -> list[Participant]:
        with self._session() as session:
            participants = list(
                session.scalars(
                    select(ParticipantModel).order_by(
                        ParticipantModel.created_at.asc(), ParticipantModel.id.asc())
                )
            )
            return [self._participant_from_model(participant) for participant in participants]

    def has_raffle_results(self) -> bool:
        with self._session() as session:
            result_id = session.scalar(select(RaffleResultModel.id).limit(1))
            return result_id is not None

    def create_raffle_results(self, assignments: Sequence[PrizeAssignment]) -> list[PrizeWinner]:
        if not assignments:
            return []

        created_at = utc_now()
        rows = [
            RaffleResultModel(
                participant_id=assignment.participant_id,
                prize_code=assignment.prize_code,
                prize_title=assignment.prize_title,
                prize_order=assignment.prize_order,
                created_at=created_at,
            )
            for assignment in assignments
        ]

        with self._session() as session:
            try:
                session.execute(text("SELECT pg_advisory_xact_lock(847621)"))
            except DatabaseError:
                session.rollback()
            if session.scalar(select(RaffleResultModel.id).limit(1)) is not None:
                return self.list_results()
            session.add_all(rows)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return self.list_results()

        return self.list_results()

    def get_result_by_telegram_user_id(self, telegram_user_id: int) -> PrizeWinner | None:
        with self._session() as session:
            row = session.execute(
                select(RaffleResultModel, ParticipantModel)
                .join(ParticipantModel, ParticipantModel.id == RaffleResultModel.participant_id)
                .where(ParticipantModel.telegram_user_id == telegram_user_id)
            ).first()
            return self._winner_from_models(row[0], row[1]) if row is not None else None

    def list_results(self) -> list[PrizeWinner]:
        with self._session() as session:
            rows = session.execute(
                select(RaffleResultModel, ParticipantModel)
                .join(ParticipantModel, ParticipantModel.id == RaffleResultModel.participant_id)
                .order_by(
                    RaffleResultModel.prize_order.asc(),
                    ParticipantModel.created_at.asc(),
                    ParticipantModel.id.asc(),
                )
            ).all()
            return [self._winner_from_models(result, participant) for result, participant in rows]

    def list_pending_notifications(self) -> list[PrizeWinner]:
        with self._session() as session:
            rows = session.execute(
                select(RaffleResultModel, ParticipantModel)
                .join(ParticipantModel, ParticipantModel.id == RaffleResultModel.participant_id)
                .where(RaffleResultModel.notified_at.is_(None))
                .order_by(
                    RaffleResultModel.prize_order.asc(),
                    ParticipantModel.created_at.asc(),
                    ParticipantModel.id.asc(),
                )
            ).all()
            return [self._winner_from_models(result, participant) for result, participant in rows]

    def mark_result_notified(self, result_id: int) -> None:
        with self._session() as session:
            result = session.get(RaffleResultModel, result_id)
            if result is None:
                return
            result.notified_at = utc_now()
            session.commit()

    def get_meta(self, key: str) -> str | None:
        with self._session() as session:
            row = session.get(AppMetaModel, key)
            return None if row is None else row.value

    def set_meta(self, key: str, value: str) -> None:
        with self._session() as session:
            meta = session.get(AppMetaModel, key)
            if meta is None:
                session.add(AppMetaModel(key=key, value=value))
            else:
                meta.value = value
            session.commit()

    def _session(self):
        return self._session_factory()

    @staticmethod
    def _participant_from_model(model: ParticipantModel | None) -> Participant | None:
        if model is None:
            return None
        return Participant(
            id=model.id,
            telegram_user_id=model.telegram_user_id,
            username=model.username,
            full_name=model.full_name,
            phone=model.phone,
            company=model.company,
            position=model.position,
            created_at=model.created_at,
            gsheets_synced_at=model.gsheets_synced_at,
            gsheets_error=model.gsheets_error,
        )

    @staticmethod
    def _winner_from_models(result: RaffleResultModel, participant: ParticipantModel) -> PrizeWinner:
        return PrizeWinner(
            result_id=result.id,
            participant_id=participant.id,
            telegram_user_id=participant.telegram_user_id,
            username=participant.username,
            full_name=participant.full_name,
            phone=participant.phone,
            company=participant.company,
            position=participant.position,
            prize_code=result.prize_code,
            prize_title=result.prize_title,
            prize_order=result.prize_order,
            created_at=result.created_at,
            notified_at=result.notified_at,
        )
