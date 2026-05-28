import asyncio
from datetime import datetime

from celery import Celery

from config import load_config
from raffle_logic import draw_results, is_raffle_due
from runtime import build_runtime, close_runtime


config = load_config()

celery_app = Celery(
    "sibtrans_giveaway",
    broker=config.celery_broker_url,
    backend=config.celery_result_backend,
)
celery_app.conf.update(
    timezone=config.raffle_at.tzinfo.key if hasattr(
        config.raffle_at.tzinfo, "key") else "UTC",
    enable_utc=True,
    beat_schedule={
        "process-raffle": {
            "task": "sibtrans_giveaway.process_raffle",
            "schedule": config.celery_raffle_check_seconds,
            "kwargs": {"force": False},
        }
    },
)


@celery_app.task(name="sibtrans_giveaway.process_raffle")
def process_raffle_task(force: bool = False) -> str:
    return asyncio.run(_process_raffle(force=force))


async def _process_raffle(*, force: bool) -> str:
    runtime = build_runtime(with_dispatcher=False)
    try:
        if not runtime.repository.has_raffle_results() and not force and not is_raffle_due(
            datetime.now(
                runtime.config.raffle_at.tzinfo), runtime.config.raffle_at
        ):
            return "before-draw"

        if not runtime.repository.has_raffle_results():
            participants = runtime.repository.list_participants()
            if not participants:
                return "no-participants"
            assignments = draw_results(
                participants,
                runtime.config.competitive_prizes,
                runtime.config.stickerpack_prize,
            )
            runtime.repository.create_raffle_results(assignments)

        await runtime.service.notify_pending_winners(runtime.bot)
        await runtime.service.post_results_if_needed(runtime.bot)
        return "processed"
    finally:
        await close_runtime(runtime)
