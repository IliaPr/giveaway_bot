import logging
from contextlib import asynccontextmanager

from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request, status

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
    webhook_url = config.webhook_url
    if webhook_url is None:
        raise RuntimeError(
            "WEBHOOK_BASE_URL is required to run the bot in webhook mode.")

    await bot.delete_webhook(drop_pending_updates=False)
    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=dispatcher.resolve_used_update_types(),
        secret_token=config.webhook_secret_token,
    )

    try:
        yield
    finally:
        await bot.delete_webhook(drop_pending_updates=False)
        await close_runtime(runtime)


app = FastAPI(lifespan=lifespan)
admin = setup_admin(app, config)


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post(config.webhook_path)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    if config.webhook_secret_token and x_telegram_bot_api_secret_token != config.webhook_secret_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret token")

    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dispatcher.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    try:
        import uvicorn

        uvicorn.run(app, host=config.server_host, port=config.server_port)
    except (KeyboardInterrupt, SystemExit):
        pass
