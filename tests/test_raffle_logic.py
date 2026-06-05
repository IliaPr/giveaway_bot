import unittest
from datetime import datetime, timezone

from config import PrizeCategory
from db.schemas import PrizeWinner
from raffle_logic import build_results_post


class RaffleLogicTests(unittest.TestCase):
    def test_build_results_post_uses_dynamic_titles_and_date(self) -> None:
        result = PrizeWinner(
            result_id=1,
            participant_id=1,
            telegram_user_id=123,
            username="winner",
            full_name="Иван Иванов",
            phone=None,
            company="ООО Ромашка",
            position=None,
            prize_code="certificate",
            prize_title="Главный приз",
            prize_order=1,
            created_at=datetime.now(timezone.utc),
            notified_at=None,
        )
        competitive_prizes = (
            PrizeCategory(
                code="certificate",
                title="Главный приз",
                winner_count=1,
                order=1,
            ),
        )
        stickerpack_prize = PrizeCategory(
            code="stickerpack",
            title="уникальный стикерпак для Telegram",
            winner_count=0,
            order=2,
        )

        text = build_results_post(
            [result],
            competitive_prizes=competitive_prizes,
            stickerpack_prize=stickerpack_prize,
            raffle_display_text="5 июня в 18:00",
        )

        self.assertIn("5 июня в 18:00", text)
        self.assertIn("Главный приз -", text)
        self.assertNotIn("4 июня", text)
        self.assertNotIn("Сертификат на перевозку 100 000 рублей", text)


if __name__ == "__main__":
    unittest.main()
