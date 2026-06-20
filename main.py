import asyncio
import logging
from config import BOT_TOKEN, ADMIN_ID

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

import database as db
from middlewares import UserRegisterMiddleware
from handlers import admin, user

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


async def main():
    # Ma'lumotlar bazasini ishga tushirish
    logger.info("Ma'lumotlar bazasi ishga tushirilmoqda...")
    await db.init_db()
    logger.info("Ma'lumotlar bazasi tayyor!")

    # Bot va Dispatcher yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware qo'shish
    dp.message.middleware(UserRegisterMiddleware())
    dp.callback_query.middleware(UserRegisterMiddleware())

    # Handler'larni ro'yxatdan o'tkazish
    # Admin handler avval (chunki undan keyin user handler barcha matnni ushlaydi)
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Bot ma'lumotlarini olish
    bot_info = await bot.get_me()
    logger.info(f"Bot ishga tushirildi: @{bot_info.username}")
    logger.info(f"Admin ID: {ADMIN_ID}")

    # Barcha foydalanuvchilar uchun buyruqlar — bo'sh
    await bot.set_my_commands([], scope=BotCommandScopeDefault())

    # Faqat adminga ko'rinadigan buyruqlar
    admin_commands = [
        BotCommand(command="admin", description="👑 Admin panel"),
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
    ]
    await bot.set_my_commands(
        admin_commands,
        scope=BotCommandScopeChat(chat_id=ADMIN_ID)
    )

    # Admin'ga xabar yuborish
    try:
        await bot.send_message(
            ADMIN_ID,
            f"✅ <b>Bot ishga tushirildi!</b>\n\n"
            f"🤖 Bot: @{bot_info.username}\n"
            f"👑 Admin ID: {ADMIN_ID}\n\n"
            f"Admin panelni ochish uchun /admin buyrug'ini yuboring.",
        )
    except Exception as e:
        logger.warning(f"Admin'ga xabar yuborib bo'lmadi: {e}")

    # Polling boshlash
    logger.info("Polling boshlanyapti...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    asyncio.run(main())
