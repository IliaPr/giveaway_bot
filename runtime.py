from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from config import Config, load_config
from db.repository import Repository
from google_sheets import GoogleSheetsClient
from tg.service import GiveawayService


@dataclass(slots=True)
class AppRuntime:
    config: Config
    repository: Repository
    sheets_client: GoogleSheetsClient
    service: GiveawayService
    bot: Bot
    dispatcher: Dispatcher | None = None


def build_runtime(*, with_dispatcher: bool) -> AppRuntime:
    config = load_config()
    repository = Repository(config.database_dsn)
    sheets_client = GoogleSheetsClient(config)
    service = GiveawayService(
        config=config,
        repository=repository,
        sheets_client=sheets_client,
    )
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dispatcher: Dispatcher | None = None
    if with_dispatcher:
        from tg.handlers import create_router

        storage = RedisStorage.from_url(config.redis_url)
        dispatcher = Dispatcher(storage=storage)
        dispatcher.include_router(create_router(service))

    return AppRuntime(
        config=config,
        repository=repository,
        sheets_client=sheets_client,
        service=service,
        bot=bot,
        dispatcher=dispatcher,
    )


async def close_runtime(runtime: AppRuntime) -> None:
    if runtime.dispatcher is not None:
        await runtime.dispatcher.storage.close()
    await runtime.bot.session.close()
