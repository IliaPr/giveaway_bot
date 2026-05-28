from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def subscription_keyboard(subscription_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться", url=subscription_url)],
            [InlineKeyboardButton(text="Я подписался",
                                  callback_data="recheck_subscription")],
        ]
    )
