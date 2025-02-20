from contextlib import asynccontextmanager

import uvicorn

from app.bot.create_bot import dp, start_bot, bot, stop_bot
from app.config import settings, broker, scheduler
from aiogram.types import Update
from fastapi import FastAPI, Request
from loguru import logger
from app.api.router import router as router_fast_stream, disable_booking



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Bot is  starting...")
    await start_bot()
    await broker.start()
    scheduler.start()
    scheduler.add_job(
        disable_booking,
        trigger="interval",
        minutes=30,
        id="disable_booking_task",
        replace_existing=True
    )
    webhook_url = settings.hook_url
    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True
    )
    logger.success(f"Webhook is set: {webhook_url}")
    yield
    logger.info("Bot is stopping...")
    await stop_bot()
    await broker.close()
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
app.include_router(router_fast_stream)
@app.post("/webhook")
async def webhook(request: Request) -> None:
    logger.info("Получен запрос с вебхука.")
    try:
        update_data = await request.json()
        update = Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_update(bot, update)
        logger.info("Обновление успешно обработано.")
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления с вебхука: {e}")


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, host="localhost", reload=True)