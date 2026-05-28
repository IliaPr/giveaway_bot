import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from admin import setup_admin
from runtime import build_runtime, close_runtime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


runtime = build_runtime(with_dispatcher=True)
config = runtime.config
bot = runtime.bot
dispatcher = runtime.dispatcher


@asynccontextmanager
async def lifespan(_: FastAPI):
    await bot.delete_webhook(drop_pending_updates=False)
    polling_task = asyncio.create_task(
        dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
            handle_signals=False,
            close_bot_session=False,
        )
    )

    try:
        yield
    finally:
        if not polling_task.done():
            await dispatcher.stop_polling()
        await polling_task
        await close_runtime(runtime)


app = FastAPI(lifespan=lifespan)
admin = setup_admin(app, config)


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":
    try:
        import uvicorn

        uvicorn.run(app, host=config.server_host, port=config.server_port)
    except (KeyboardInterrupt, SystemExit):
        pass
