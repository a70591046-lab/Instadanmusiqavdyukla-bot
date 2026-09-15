import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from aiogram.types import BotCommand
from config import BOT_TOKEN
from database import init_db
from handlers import start, dumaloq, media, music, admin, extra_features
from services.dpi import start_dpi_service, stop_dpi_service

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

import os
from aiohttp import web

async def start_health_server():
    port_str = os.getenv("PORT", "").strip()
    if not port_str:
        return None
    try:
        port = int(port_str)
        app = web.Application()
        async def ping(request):
            return web.Response(text="Bot is running 24/7!")
        app.router.add_get("/", ping)
        app.router.add_get("/health", ping)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Bulutli server uchun health-check 0.0.0.0:{port} da ishga tushirildi.")
        return runner
    except Exception as e:
        logger.warning(f"Health server xatosi: {e}")
        return None

def prevent_sleep():
    """Windows tizimi fon rejimida uxlab qolmasligi va 24/7 ishlashi uchun"""
    if sys.platform == "win32":
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_AWAYMODE_REQUIRED = 0x00000040
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
            logger.info("Windows 24/7 rejim faollashtirildi: tizim uxlab qolmaydi, bot to'xtovsiz ishlaydi.")
        except Exception as e:
            logger.warning(f"SetThreadExecutionState xatosi: {e}")

async def main():
    logger.info("Bot ishga tushirilmoqda...")

    # 24/7 rejim (tizim uxlab qolmasligi uchun)
    prevent_sleep()

    # Bulutli server (Render/Koyeb) uchun veb-server
    web_runner = await start_health_server()

    # Ma'lumotlar bazasini ishga tushirish
    init_db()

    # Instagram va YouTube blokirovkalarini aylanib o'tish uchun lokal ByeDPI ni yoqish
    start_dpi_service()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    # Routerlarni ulash (tartib muhim!)
    dp.include_router(admin.router)
    dp.include_router(extra_features.router)
    dp.include_router(start.router)
    dp.include_router(dumaloq.router)
    dp.include_router(media.router)
    dp.include_router(music.router)

    # Bot menyu buyruqlarini ro'yxatdan o'tkazish
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="dumaloq", description="🔵 Dumaloq video qilish"),
        BotCommand(command="4k", description="✨ 4K effekt berish"),
        BotCommand(command="musiqa", description="🎵 Musiqa qidirish / yuklash"),
        BotCommand(command="konsert", description="🏟️ Konsert musiqasi"),
        BotCommand(command="ega", description="👑 Admin panel (@Muhammadali00010)"),
        BotCommand(command="help", description="📖 Qo'llanma"),
    ])

    # Bot ma'lumotlarini olish
    bot_info = await bot.get_me()
    logger.info(f"Bot muvaffaqiyatli ulandi: @{bot_info.username} ({bot_info.first_name})")

    # Eski kutilayotgan xabarlarni tozalash (drop pending updates)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Polling boshlandi... Bot xabarlarni qabul qilishga tayyor!")
    try:
        await dp.start_polling(bot)
    finally:
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()
        stop_dpi_service()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
        stop_dpi_service()

