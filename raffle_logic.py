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
    titles: dict[str, str] = {}
    stickerpack_count = 0

    for result in results:
        if result.prize_code == stickerpack_prize.code:
            stickerpack_count += 1
            continue
        grouped[result.prize_code].append(result)
        titles[result.prize_code] = result.prize_title

    lines = ["Итоги розыгрыша «Байт Транзит»", ""]
    for prize in competitive_prizes:
        winners = grouped.get(prize.code, [])
        if not winners:
            continue
        lines.append(escape(titles[prize.code]))
        for index, winner in enumerate(winners, start=1):
            company_suffix = f" ({escape(winner.company)})" if winner.company else ""
            display_name = winner_display_name(winner)
            lines.append(f"{index}. {escape(display_name)}{company_suffix}")
        lines.append("")

    if stickerpack_count:
        lines.append(
            f"{escape(stickerpack_prize.title)} получают все остальные участники: {stickerpack_count}"
        )

    return "\n".join(lines).strip()


def winner_display_name(winner: PrizeWinner) -> str:
    if winner.full_name:
        return winner.full_name
    if winner.username:
        return f"@{winner.username}"
    return str(winner.telegram_user_id)


def is_raffle_due(now: datetime, raffle_at: datetime) -> bool:
    return now >= raffle_at
