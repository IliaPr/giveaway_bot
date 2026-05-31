import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from celery_app import process_raffle_task
from db.repository import DuplicateParticipantError
from raffle_logic import is_raffle_due
from tg.keyboards import subscription_keyboard
from tg.states import RegistrationForm

if TYPE_CHECKING:
    from tg.service import GiveawayService


logger = logging.getLogger(__name__)

MAX_TEXT_FIELD_LENGTH = 1024


def _normalize_full_name(full_name: str) -> str:
    return " ".join(full_name.split())


def _is_valid_full_name(full_name: str) -> bool:
    words = full_name.split()
    return 2 <= len(words) <= 3


def _is_valid_phone(phone: str) -> bool:
    if not phone.startswith("+"):
        return False
    if not re.fullmatch(r"\+[\d\s()\-]+", phone):
        return False
    digits_only = re.sub(r"\D", "", phone)
    return 10 <= len(digits_only) <= 15


def _normalize_phone(phone: str) -> str:
    return f"+{re.sub(r'\D', '', phone)}"


def _is_text_too_long(value: str) -> bool:
    return len(value) > MAX_TEXT_FIELD_LENGTH


def _is_registration_closed(service: "GiveawayService") -> bool:
    return is_raffle_due(
        datetime.now(service.config.raffle_at.tzinfo),
        service.config.raffle_at,
    )


def create_router(service: "GiveawayService") -> Router:
    router = Router(name="giveaway")

    @router.message(CommandStart())
    async def start_registration(message: Message, state: FSMContext, bot: Bot) -> None:
        if message.from_user is None:
            return

        existing_participant = service.repository.get_participant_by_telegram_user_id(
            message.from_user.id
        )
        if existing_participant is not None:
            result = service.repository.get_result_by_telegram_user_id(
                message.from_user.id)
            await state.clear()
            await message.answer(
                service.format_existing_registration_message(result),
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        if _is_registration_closed(service):
            await state.clear()
            await message.answer("Регистрация на розыгрыш уже закрыта.")
            return

        if not await service.is_subscribed(bot, message.from_user.id):
            await state.clear()
            await message.answer(
                "Чтобы участвовать в розыгрыше, подпишитесь на канал @sbtrntst и затем подтвердите подписку.",
                reply_markup=subscription_keyboard(
                    service.config.subscription_url),
            )
            return

        await state.set_state(RegistrationForm.full_name)
        await message.answer("Введите ФИО:", reply_markup=ReplyKeyboardRemove())

    @router.callback_query(F.data == "recheck_subscription")
    async def recheck_subscription(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return

        existing_participant = service.repository.get_participant_by_telegram_user_id(
            callback.from_user.id
        )
        if existing_participant is not None:
            result = service.repository.get_result_by_telegram_user_id(
                callback.from_user.id)
            await state.clear()
            await callback.message.answer(
                service.format_existing_registration_message(result),
                reply_markup=ReplyKeyboardRemove(),
            )
            await callback.answer()
            return

        if _is_registration_closed(service):
            await state.clear()
            await callback.message.answer(
                "Регистрация на розыгрыш уже закрыта.",
                reply_markup=ReplyKeyboardRemove(),
            )
            await callback.answer()
            return

        if not await service.is_subscribed(bot, callback.from_user.id):
            await callback.answer(
                "Подписка пока не найдена. Проверьте канал и попробуйте снова.",
                show_alert=True,
            )
            return

        await state.set_state(RegistrationForm.full_name)
        await callback.message.answer(
            "Подписка подтверждена. Введите ФИО:",
            reply_markup=ReplyKeyboardRemove(),
        )
        await callback.answer()

    @router.message(Command("run_raffle"))
    async def run_raffle_command(message: Message, bot: Bot) -> None:
        if message.from_user is None or message.from_user.id not in service.config.admin_ids:
            await message.answer("Команда недоступна.")
            return

        task = process_raffle_task.delay(force=True)
        await message.answer(f"Розыгрыш поставлен в очередь. Task ID: {task.id}")

    @router.message(RegistrationForm.full_name)
    async def capture_full_name(message: Message, state: FSMContext) -> None:
        if _is_registration_closed(service):
            await state.clear()
            await message.answer("Регистрация на розыгрыш уже закрыта.")
            return

        full_name = _normalize_full_name((message.text or "").strip())
        if _is_text_too_long(full_name):
            await message.answer(
                "Сообщение слишком длинное. Максимальная длина: 1024 символа."
            )
            return
        if not _is_valid_full_name(full_name):
            await message.answer("Укажите ФИО из 2 или 3 слов. <i>Например: Иванов Иван Иванович</i>", parse_mode="HTML")
            return

        await state.update_data(full_name=full_name)
        await state.set_state(RegistrationForm.phone)
        await message.answer("Введите телефон: <i>Например: +7 123 456 78 90</i>", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

    @router.message(RegistrationForm.phone)
    async def capture_phone(message: Message, state: FSMContext) -> None:
        if _is_registration_closed(service):
            await state.clear()
            await message.answer("Регистрация на розыгрыш уже закрыта.")
            return

        phone = (message.text or "").strip()
        if _is_text_too_long(phone):
            await message.answer(
                "Сообщение слишком длинное. Максимальная длина: 1024 символа."
            )
            return
        if not _is_valid_phone(phone):
            await message.answer("Укажите корректный телефон. <i>Например: +7 123 456 78 90</i>", parse_mode="HTML")
            return

        await state.update_data(phone=_normalize_phone(phone))
        await state.set_state(RegistrationForm.company)
        await message.answer("Укажите название компании:", reply_markup=ReplyKeyboardRemove())

    @router.message(RegistrationForm.company)
    async def capture_company(message: Message, state: FSMContext) -> None:
        if _is_registration_closed(service):
            await state.clear()
            await message.answer("Регистрация на розыгрыш уже закрыта.")
            return

        company = (message.text or "").strip()
        if _is_text_too_long(company):
            await message.answer(
                "Сообщение слишком длинное. Максимальная длина: 1024 символа."
            )
            return
        if len(company) < 2:
            await message.answer("Укажите название компании:", reply_markup=ReplyKeyboardRemove())
            return

        await state.update_data(company=company)
        await state.set_state(RegistrationForm.position)
        await message.answer("Укажите Вашу должность:", reply_markup=ReplyKeyboardRemove())

    @router.message(RegistrationForm.position)
    async def capture_position(message: Message, state: FSMContext) -> None:
        if message.from_user is None:
            return

        if _is_registration_closed(service):
            await state.clear()
            await message.answer("Регистрация на розыгрыш уже закрыта.")
            return

        position = (message.text or "").strip()
        if _is_text_too_long(position):
            await message.answer(
                "Сообщение слишком длинное. Максимальная длина: 1024 символа."
            )
            return
        if len(position) < 2:
            await message.answer("Укажите Вашу должность:", reply_markup=ReplyKeyboardRemove())
            return

        data = await state.get_data()
        try:
            _, sync_error = await service.save_registration(
                telegram_user_id=message.from_user.id,
                username=message.from_user.username,
                full_name=str(data["full_name"]),
                phone=str(data["phone"]),
                company=str(data["company"]),
                position=position,
            )
        except DuplicateParticipantError:
            result = service.repository.get_result_by_telegram_user_id(
                message.from_user.id)
            await state.clear()
            await message.answer(
                service.format_existing_registration_message(result),
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        await state.clear()
        confirmation = f"Вы зарегистрированы! Розыгрыш пройдёт {service.config.raffle_display_text}"
        if sync_error:
            logger.warning(
                "Participant %s was registered locally, but Google Sheets sync failed: %s",
                message.from_user.id,
                sync_error,
            )
        await message.answer(confirmation, reply_markup=ReplyKeyboardRemove())

    return router
