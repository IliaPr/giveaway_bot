import os
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class PrizeCategory:
    code: str
    title: str
    winner_count: int
    order: int


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str
    celery_raffle_check_seconds: int
    webhook_base_url: str
    webhook_path: str
    webhook_secret_token: str | None
    server_host: str
    server_port: int
    subscription_chat_id: str
    subscription_url: str
    results_chat_id: str
    raffle_at: datetime
    raffle_display_text: str
    database_dsn: str
    google_sheet_id: str | None
    google_worksheet_title: str
    google_service_account_file: str | None
    google_service_account_json: str | None
    admin_username: str | None
    admin_password: str | None
    admin_session_secret: str
    admin_base_url: str
    admin_title: str
    admin_ids: frozenset[int]
    certificate_title: str
    certificate_winners: int
    merch_1_title: str
    merch_1_winners: int
    merch_2_title: str
    merch_2_winners: int
    merch_3_title: str
    merch_3_winners: int
    stickerpack_title: str
    stickerpack_url: str | None

    @property
    def competitive_prizes(self) -> tuple[PrizeCategory, ...]:
        prizes = (
            PrizeCategory(
                code="certificate",
                title=self.certificate_title,
                winner_count=max(self.certificate_winners, 0),
                order=1,
            ),
            PrizeCategory(
                code="merch_1",
                title=self.merch_1_title,
                winner_count=max(self.merch_1_winners, 0),
                order=2,
            ),
            PrizeCategory(
                code="merch_2",
                title=self.merch_2_title,
                winner_count=max(self.merch_2_winners, 0),
                order=3,
            ),
            PrizeCategory(
                code="merch_3",
                title=self.merch_3_title,
                winner_count=max(self.merch_3_winners, 0),
                order=4,
            ),
        )
        return tuple(prize for prize in prizes if prize.winner_count > 0)

    @property
    def stickerpack_prize(self) -> PrizeCategory:
        return PrizeCategory(
            code="stickerpack",
            title=self.stickerpack_title,
            winner_count=0,
            order=5,
        )

    @property
    def webhook_url(self) -> str:
        base_url = self.webhook_base_url.rstrip("/")
        path = self.webhook_path if self.webhook_path.startswith(
            "/") else f"/{self.webhook_path}"
        return f"{base_url}{path}"


def load_config() -> Config:
    bot_token = _require_env("BOT_TOKEN")
    raffle_timezone = os.getenv("RAFFLE_TIMEZONE", "Asia/Novosibirsk")
    raffle_at = _parse_datetime(
        os.getenv("RAFFLE_AT", "2026-06-04T18:00:00"),
        raffle_timezone,
    )

    return Config(
        bot_token=bot_token,
        redis_url=_require_env("REDIS_URL"),
        celery_broker_url=os.getenv(
            "CELERY_BROKER_URL", os.getenv("REDIS_URL", "")),
        celery_result_backend=os.getenv(
            "CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "")),
        celery_raffle_check_seconds=_parse_int_env(
            "CELERY_RAFFLE_CHECK_SECONDS", 60),
        webhook_base_url=_require_env("WEBHOOK_BASE_URL"),
        webhook_path=os.getenv("WEBHOOK_PATH", "/telegram/webhook"),
        webhook_secret_token=os.getenv("WEBHOOK_SECRET_TOKEN"),
        server_host=os.getenv("WEBHOOK_HOST", "0.0.0.0"),
        server_port=_parse_int_env("WEBHOOK_PORT", 8080),
        subscription_chat_id=os.getenv("SUBSCRIPTION_CHAT_ID", "@sibtrans_ru"),
        subscription_url=os.getenv(
            "SUBSCRIPTION_URL", "https://t.me/sibtrans_ru"),
        results_chat_id=os.getenv("RESULTS_CHAT_ID", "@sibtrans_ru"),
        raffle_at=raffle_at,
        raffle_display_text=os.getenv("RAFFLE_DISPLAY_TEXT", "4 июня в 18:00"),
        database_dsn=_require_database_dsn(),
        google_sheet_id=os.getenv("GOOGLE_SHEET_ID"),
        google_worksheet_title=os.getenv(
            "GOOGLE_WORKSHEET_TITLE", "Регистрация"),
        google_service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
        google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
        admin_username=os.getenv("ADMIN_USERNAME"),
        admin_password=os.getenv("ADMIN_PASSWORD"),
        admin_session_secret=os.getenv(
            "ADMIN_SESSION_SECRET",
            os.getenv("WEBHOOK_SECRET_TOKEN") or bot_token,
        ),
        admin_base_url=os.getenv("ADMIN_BASE_URL", "/admin"),
        admin_title=os.getenv("ADMIN_TITLE", "Sibtrans Admin"),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        certificate_title=os.getenv(
            "CERTIFICATE_TITLE", "🏆 Сертификат на перевозку"
        ),
        certificate_winners=_parse_int_env("CERTIFICATE_WINNERS", 1),
        merch_1_title=os.getenv("MERCH_1_TITLE", "🎁 Увлажнитель воздуха"),
        merch_1_winners=_parse_int_env("MERCH_1_WINNERS", 1),
        merch_2_title=os.getenv("MERCH_2_TITLE", "🎁 Термос"),
        merch_2_winners=_parse_int_env("MERCH_2_WINNERS", 2),
        merch_3_title=os.getenv("MERCH_3_TITLE", "🎁 Кружка"),
        merch_3_winners=_parse_int_env("MERCH_3_WINNERS", 5),
        stickerpack_title=os.getenv(
            "STICKERPACK_TITLE", "🎁 Стикерпак Bait Tranzit"),
        stickerpack_url=os.getenv(
            "STICKERPACK_URL", "https://t.me/addstickers/bait_tranzit"
        ),
    )


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f"Environment variable {name} is required.")


def _require_database_dsn() -> str:

    db_user = _require_env("DB_USER")
    db_password = _require_env("DB_PASSWORD")
    db_host = _require_env("DB_HOST")
    db_port = _require_env("DB_PORT")
    db_name = _require_env("DB_NAME")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def _normalize_database_dsn(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def _parse_datetime(value: str, timezone_name: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        return parsed
    return parsed.replace(tzinfo=ZoneInfo(timezone_name))


def _parse_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        return int(raw_value)
    except ValueError as error:
        raise RuntimeError(
            f"Environment variable {name} must be an integer.") from error


def _parse_admin_ids(raw_value: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw_value.split(","):
        candidate = part.strip()
        if not candidate:
            continue
        try:
            ids.add(int(candidate))
        except ValueError as error:
            raise RuntimeError(
                "ADMIN_IDS must contain comma-separated integers.") from error
    return frozenset(ids)
