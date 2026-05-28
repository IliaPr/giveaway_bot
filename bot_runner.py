import asyncio
import logging

from runtime import build_runtime, close_runtime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


async def main() -> None:
    runtime = build_runtime(with_dispatcher=True)
    try:
        await runtime.bot.delete_webhook(drop_pending_updates=False)
        await runtime.dispatcher.start_polling(
            runtime.bot,
            allowed_updates=runtime.dispatcher.resolve_used_update_types(),
            handle_signals=True,
            close_bot_session=False,
        )
    finally:
        await close_runtime(runtime)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
