"""VELTON single-container entrypoint: FastAPI + Telegram polling."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("velton")


async def serve() -> None:
    port = int(os.environ.get("PORT", "3000"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    token = os.environ.get("BOT_TOKEN", "").strip()
    demo = os.environ.get("DEMO_MODE", "0") == "1"
    if not token and not demo:
        raise RuntimeError("BOT_TOKEN is missing; set it in hosting environment. DEMO_MODE=1 is only for local tests")

    config = uvicorn.Config("server:app", host="0.0.0.0", port=port,
                            log_level="info", lifespan="on", access_log=True)
    web = uvicorn.Server(config)
    web_task = asyncio.create_task(web.serve(), name="velton-api")
    tasks = [web_task]
    if token:
        from bot import main as bot_main
        tasks.append(asyncio.create_task(bot_main(), name="velton-telegram-bot"))
        log.info("Starting VELTON API on port %s and Telegram bot", port)
    else:
        log.warning("DEMO_MODE=1: API only; Telegram polling not started")

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task.cancelled():
                continue
            error = task.exception()
            if error is not None:
                raise RuntimeError(f"VELTON component {task.get_name()} failed") from error
            if task is web_task and not web.started and not web.should_exit:
                raise RuntimeError("VELTON API did not start")
            if task is not web_task:
                raise RuntimeError("Telegram bot stopped unexpectedly")
    finally:
        web.should_exit = True
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass
