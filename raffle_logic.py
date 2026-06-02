from collections import defaultdict
from datetime import datetime
from html import escape
from random import SystemRandom

from config import PrizeCategory
from db.schemas import Participant, PrizeAssignment, PrizeWinner


randomizer = SystemRandom()


def draw_results(
    participants: list[Participant],
    competitive_prizes: tuple[PrizeCategory, ...],
    stickerpack_prize: PrizeCategory,
) -> list[PrizeAssignment]:
    available = participants[:]
    assignments: list[PrizeAssignment] = []

    for prize in competitive_prizes:
        if not available:
            break
        winners = randomizer.sample(available, k=min(
            prize.winner_count, len(available)))
        winner_ids = {winner.id for winner in winners}
        assignments.extend(
            PrizeAssignment(
                participant_id=winner.id,
                prize_code=prize.code,
                prize_title=prize.title,
                prize_order=prize.order,
            )
            for winner in winners
        )
        available = [
            participant for participant in available if participant.id not in winner_ids]

    assignments.extend(
        PrizeAssignment(
            participant_id=participant.id,
            prize_code=stickerpack_prize.code,
            prize_title=stickerpack_prize.title,
            prize_order=stickerpack_prize.order,
        )
        for participant in available
    )
    return assignments


def build_personal_result_text(
    result: PrizeWinner,
    *,
    stickerpack_prize_code: str,
    stickerpack_url: str | None,
) -> str:
    if result.prize_code == stickerpack_prize_code and stickerpack_url:
        return (
            "🎉 Поздравляем!\n\n"
            "Вы стали победителем розыгрыша от «Байт Транзит»\n\n"
            f"Ваш приз: {escape(result.prize_title)}\n"
            f"Стикерпак: {escape(stickerpack_url)}\n\n"
            "Спасибо за участие и отличного вам дня на выставке!"
        )

    return (
        "🎉 Поздравляем!\n\n"
        "Вы стали победителем розыгрыша от «Байт Транзит»\n\n"
        f"Ваш приз: {escape(result.prize_title)}\n\n"
        "Спасибо, что приняли участие! Наш менеджер свяжется с вами в ближайшее время для вручения приза\n\n"
        "Спасибо за участие и отличного вам дня на выставке!"
    )


def build_results_post(
    results: list[PrizeWinner],
    *,
    competitive_prizes: tuple[PrizeCategory, ...],
    stickerpack_prize: PrizeCategory,
) -> str:
    grouped: dict[str, list[PrizeWinner]] = defaultdict(list)

    for result in results:
        if result.prize_code == stickerpack_prize.code:
            continue
        grouped[result.prize_code].append(result)

    lines = [
        "🎉Итоги розыгрыша среди участников выставки «Уголь России и Майнинг» в Новокузнецке",
        "",
        "Добрый день! С 2 по 5 июня команда «Байт Транзит» принимает участие в XXXIV Международной специализированной выставке технологий горных разработок «Уголь России и Майнинг» в Новокузнецке. Среди участников выставки компания «Байт Транзит» провела беспроигрышную лотерею. Главный приз - сертификат на 100 000 руб. на сборные грузоперевозки по России. Розыгрыш состоялся 4 июня в 18.00 по местному времени (14:00 по МСК)",
        "",
        "Поздравляем:",
        "",
    ]

    prize_labels = {
        "certificate": "🏆 Сертификат на перевозку 100 000 рублей —",
        "merch_1": "🎁 Увлажнитель воздуха -",
        "merch_2": "🎁 Термос -",
        "merch_3": "🎁 Кружка -",
    }
    prizes_by_code = {prize.code: prize for prize in competitive_prizes}

    for prize_code, label in prize_labels.items():
        prize = prizes_by_code.get(prize_code)
        winners = grouped.get(prize_code, []) if prize else []
        lines.extend(format_public_winners_line(label, winners))

    lines.extend(
        [
            "",
            "Все остальные участники розыгрыша получили уникальные стикерпак для телеграма",
            "",
            "Благодарим всех участников за интерес к нашей компании и до встречи на других мероприятиях в вашем городе!",
            "Ваш надежный партнер «Байт Транзит» 🤝",
        ]
    )

    return "\n".join(lines).strip()


def format_public_winners_line(label: str, winners: list[PrizeWinner]) -> list[str]:
    if not winners:
        return [label]
    if len(winners) == 1:
        return [f"{label} {winner_public_name(winners[0])}"]
    return [
        label,
        *(
            f"{index}. {winner_public_name(winner)}"
            for index, winner in enumerate(winners, start=1)
        ),
    ]


def winner_public_name(winner: PrizeWinner) -> str:
    company_suffix = f" ({escape(winner.company)})" if winner.company else ""
    return f"{winner_display_name(winner)}{company_suffix}"


def winner_display_name(winner: PrizeWinner) -> str:
    if winner.username:
        username = escape(winner.username)
        mention = f'<a href="https://t.me/{username}">@{username}</a>'
        if winner.full_name:
            return f"{escape(winner.full_name)} ({mention})"
        return mention
    if winner.full_name:
        return escape(winner.full_name)
    return escape(str(winner.telegram_user_id))


def is_raffle_due(now: datetime, raffle_at: datetime) -> bool:
    return now >= raffle_at
