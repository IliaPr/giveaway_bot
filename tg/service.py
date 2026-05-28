import logging
from datetime import datetime

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ReplyKeyboardRemove

from config import Config
from db.repository import Repository, utc_now
from db.schemas import Participant, PrizeWinner
from google_sheets import GoogleSheetsClient
from raffle_logic import (
    build_personal_result_text,
    build_results_post,
)


logger = logging.getLogger(__name__)


class GiveawayService:
    def __init__(
        self,
        *,
        config: Config,
        repository: Repository,
        sheets_client: GoogleSheetsClient,
    ) -> None:
        self.config = config
        self.repository = repository
        self.sheets_client = sheets_client

    async def is_subscribed(self, bot: Bot, user_id: int) -> bool:
        try:
            member = await bot.get_chat_member(self.config.subscription_chat_id, user_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            logger.exception(
                "Failed to check channel subscription for user %s.", user_id)
            return False

        return member.status in {
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER,
        }

    async def save_registration(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        full_name: str,
        phone: str,
        company: str,
        position: str,
    ) -> tuple[Participant, str | None]:
        participant = self.repository.create_participant(
            telegram_user_id=telegram_user_id,
            username=username,
            full_name=full_name,
            phone=phone,
            company=company,
            position=position,
        )

        sync_error: str | None = None
        try:
            await self.sheets_client.append_participant(participant)
        except Exception as error:
            sync_error = str(error)
            self.repository.mark_participant_sync_error(
                participant.id, sync_error)
            logger.exception(
                "Failed to export participant %s to Google Sheets.",
                participant.telegram_user_id,
            )
        else:
            self.repository.mark_participant_synced(participant.id)

        return participant, sync_error

    def format_existing_registration_message(self, result: PrizeWinner | None) -> str:
        if result is None:
            return f"Вы уже зарегистрированы. Ждите розыгрыша {self.config.raffle_display_text}"
        return self._build_personal_result_text(result)

    async def notify_pending_winners(self, bot: Bot) -> None:
        for result in self.repository.list_pending_notifications():
            try:
                await bot.send_message(
                    chat_id=result.telegram_user_id,
                    text=self._build_personal_result_text(result),
                    reply_markup=ReplyKeyboardRemove(),
                )
            except TelegramForbiddenError:
                logger.warning(
                    "User %s blocked the bot before result notification.",
                    result.telegram_user_id,
                )
                continue
            except TelegramBadRequest:
                logger.exception(
                    "Failed to send raffle result to user %s.",
                    result.telegram_user_id,
                )
                continue

            self.repository.mark_result_notified(result.result_id)

    async def post_results_if_needed(self, bot: Bot) -> None:
        if self.repository.get_meta("results_posted_at"):
            return

        results = self.repository.list_results()
        if not results:
            return

        await bot.send_message(
            chat_id=self.config.results_chat_id,
            text=self._build_results_post(results),
        )
        self.repository.set_meta("results_posted_at", utc_now().isoformat())

    def _build_personal_result_text(self, result: PrizeWinner) -> str:
        return build_personal_result_text(
            result,
            stickerpack_prize_code=self.config.stickerpack_prize.code,
            stickerpack_url=self.config.stickerpack_url,
        )

    def _build_results_post(self, results: list[PrizeWinner]) -> str:
        return build_results_post(
            results,
            competitive_prizes=self.config.competitive_prizes,
            stickerpack_prize=self.config.stickerpack_prize,
        )
