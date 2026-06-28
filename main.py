import asyncio
import logging
import aiohttp
from config import BOT_TOKEN, ADMIN_ID

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (
    Message, CallbackQuery,
    BotCommand, BotCommandScopeDefault, BotCommandScopeChat
)

import database as db
import keyboards as kb
from middlewares import UserRegisterMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==================== FSM STATES ====================

class AddMovie(StatesGroup):
    waiting_code = State()
    waiting_file = State()
    waiting_title = State()
    waiting_description = State()

class DeleteMovie(StatesGroup):
    waiting_code = State()

class AddChannel(StatesGroup):
    waiting_channel_id = State()

class RemoveChannel(StatesGroup):
    waiting_channel_id = State()

class Broadcast(StatesGroup):
    waiting_message = State()
    confirm = State()

# ==================== ROUTERS ====================
admin_router = Router()
user_router = Router()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ==================== SUBSCRIPTION CHECK ====================

async def get_not_subscribed(bot: Bot, user_id: int) -> list:
    channels = await db.get_all_channels()
    if not channels:
        return []
    not_sub = []
    for ch_id, ch_name, ch_link in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ("left", "kicked", "banned"):
                not_sub.append((ch_id, ch_name, ch_link))
        except Exception:
            not_sub.append((ch_id, ch_name, ch_link))
    return not_sub

async def send_sub_msg(message: Message, not_sub: list):
    await message.answer(
        f"⛔️ <b>Botdan foydalanish uchun {len(not_sub)} ta kanalga obuna bo'ling!</b>\n\n"
        "Obuna bo'lib ✅ <b>Tekshirish</b> tugmasini bosing:",
        parse_mode="HTML",
        reply_markup=kb.subscription_keyboard(not_sub)
    )

# ==================== ADMIN HANDLERS ====================

@admin_router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("👑 <b>Admin Panel</b>", parse_mode="HTML", reply_markup=kb.admin_main_menu())

@admin_router.message(F.text == "❌ Bekor qilish", StateFilter("*"))
async def cancel_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=kb.admin_main_menu())

# --- KINO QO'SHISH ---

@admin_router.message(F.text == "🎬 Kino qo'shish")
async def add_movie_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddMovie.waiting_code)
    await message.answer("🔢 Kino kodini kiriting (masalan: <code>1</code>):", parse_mode="HTML", reply_markup=kb.cancel_keyboard())

@admin_router.message(AddMovie.waiting_code, F.text)
async def add_movie_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    code = message.text.strip()
    if await db.movie_exists(code):
        await message.answer(f"⚠️ <code>{code}</code> kodli kino mavjud!", parse_mode="HTML")
        return
    await state.update_data(code=code)
    await state.set_state(AddMovie.waiting_file)
    await message.answer("🎬 Kinoni yuboring (video/hujjat/audio/rasm):", reply_markup=kb.cancel_keyboard())

@admin_router.message(AddMovie.waiting_file, F.video | F.document | F.audio | F.photo)
async def add_movie_file(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.video:
        file_id, file_type = message.video.file_id, "video"
    elif message.document:
        file_id, file_type = message.document.file_id, "document"
    elif message.audio:
        file_id, file_type = message.audio.file_id, "audio"
    else:
        file_id, file_type = message.photo[-1].file_id, "photo"
    await state.update_data(file_id=file_id, file_type=file_type)
    await state.set_state(AddMovie.waiting_title)
    await message.answer("✏️ Kino nomini kiriting:", reply_markup=kb.cancel_keyboard())

@admin_router.message(AddMovie.waiting_title, F.text)
async def add_movie_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(AddMovie.waiting_description)
    await message.answer("📝 Tavsif kiriting (yoki <code>-</code>):", parse_mode="HTML", reply_markup=kb.cancel_keyboard())

@admin_router.message(AddMovie.waiting_description, F.text)
async def add_movie_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    desc = message.text.strip()
    if desc == "-":
        desc = None
    data = await state.get_data()
    await db.add_movie(data["code"], data["title"], desc, data["file_id"], data["file_type"])
    await state.clear()
    await message.answer(
        f"✅ Kino qo'shildi!\n🔢 Kod: <code>{data['code']}</code>\n🎬 Nom: <b>{data['title']}</b>",
        parse_mode="HTML", reply_markup=kb.admin_main_menu()
    )

# --- KINO O'CHIRISH ---

@admin_router.message(F.text == "🗑 Kino o'chirish")
async def delete_movie_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(DeleteMovie.waiting_code)
    await message.answer("🔢 O'chirmoqchi bo'lgan kino kodini kiriting:", reply_markup=kb.cancel_keyboard())

@admin_router.message(DeleteMovie.waiting_code, F.text)
async def delete_movie(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    code = message.text.strip()
    movie = await db.get_movie_by_code(code)
    if not movie:
        await message.answer(f"❌ <code>{code}</code> kodli kino topilmadi!", parse_mode="HTML")
        return
    await db.delete_movie(code)
    await state.clear()
    await message.answer(f"✅ <b>{movie[1]}</b> o'chirildi!", parse_mode="HTML", reply_markup=kb.admin_main_menu())

# --- KINOLAR RO'YXATI ---

@admin_router.message(F.text == "📋 Kinolar ro'yxati")
async def movies_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    movies = await db.get_all_movies()
    if not movies:
        await message.answer("📭 Kinolar yo'q.", reply_markup=kb.admin_main_menu())
        return
    text = f"🎬 <b>Kinolar</b> ({len(movies)} ta):\n\n"
    for i, (code, title, *_) in enumerate(movies, 1):
        text += f"{i}. <code>{code}</code> — <b>{title}</b>\n"
        if len(text) > 3500:
            await message.answer(text, parse_mode="HTML")
            text = ""
    if text:
        await message.answer(text, parse_mode="HTML", reply_markup=kb.admin_main_menu())

# --- KANAL QO'SHISH ---

@admin_router.message(F.text == "📢 Kanal qo'shish")
async def add_channel_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddChannel.waiting_channel_id)
    await message.answer(
        "📢 Kanal ID sini yuboring:\nMisol: <code>-1001234567890</code>\n\n⚠️ Bot kanalda <b>admin</b> bo'lishi shart!",
        parse_mode="HTML", reply_markup=kb.cancel_keyboard()
    )

@admin_router.message(AddChannel.waiting_channel_id, F.text)
async def add_channel(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip()
    if not raw.lstrip('-').isdigit():
        await message.answer("❌ Kanal ID noto'g'ri! Masalan: <code>-1001234567890</code>", parse_mode="HTML")
        return
    channel_id = raw
    try:
        bot_me = await bot.get_me()
        bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot_me.id)
        if bot_member.status not in ("administrator", "creator"):
            await message.answer("❌ Bot kanalda <b>admin emas</b>!\nBotni admin qilib qayta urinib ko'ring.", parse_mode="HTML")
            return
    except Exception as e:
        err = str(e).replace('<', '').replace('>', '')
        await message.answer(f"❌ Kanal topilmadi!\nSabab: {err}", parse_mode="HTML")
        return

    channel_name = f"Kanal {channel_id}"
    channel_link = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.telegram.org/bot{bot.token}/getChat",
                json={"chat_id": channel_id}
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    r = data["result"]
                    channel_name = r.get("title", channel_name)
                    if r.get("username"):
                        channel_link = f"https://t.me/{r['username']}"
                    elif r.get("invite_link"):
                        channel_link = r["invite_link"]
    except Exception:
        pass

    if not channel_link:
        try:
            inv = await bot.create_chat_invite_link(chat_id=channel_id)
            channel_link = inv.invite_link
        except Exception:
            channel_link = f"https://t.me/c/{str(channel_id).replace('-100', '')}"

    await db.add_channel(channel_id, channel_name, channel_link)
    await state.clear()
    await message.answer(
        f"✅ <b>{channel_name}</b> qo'shildi!\n🆔 <code>{channel_id}</code>\n🔗 {channel_link}",
        parse_mode="HTML", reply_markup=kb.admin_main_menu()
    )

# --- KANAL O'CHIRISH ---

@admin_router.message(F.text == "❌ Kanal o'chirish")
async def remove_channel_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    channels = await db.get_all_channels()
    if not channels:
        await message.answer("📭 Kanallar yo'q.", reply_markup=kb.admin_main_menu())
        return
    text = "📡 <b>Kanallar:</b>\n\n"
    for i, (ch_id, ch_name, _) in enumerate(channels, 1):
        text += f"{i}. <b>{ch_name}</b> — <code>{ch_id}</code>\n"
    text += "\nO'chirmoqchi bo'lgan kanal <b>ID</b> sini kiriting:"
    await state.set_state(RemoveChannel.waiting_channel_id)
    await message.answer(text, parse_mode="HTML", reply_markup=kb.cancel_keyboard())

@admin_router.message(RemoveChannel.waiting_channel_id, F.text)
async def remove_channel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    channel_id = message.text.strip()
    channels = await db.get_all_channels()
    if channel_id not in [ch[0] for ch in channels]:
        await message.answer(f"❌ <code>{channel_id}</code> topilmadi!", parse_mode="HTML")
        return
    await db.remove_channel(channel_id)
    await state.clear()
    await message.answer(f"✅ <code>{channel_id}</code> o'chirildi!", parse_mode="HTML", reply_markup=kb.admin_main_menu())

# --- KANALLAR RO'YXATI ---

@admin_router.message(F.text == "📡 Kanallar ro'yxati")
async def channels_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    channels = await db.get_all_channels()
    if not channels:
        await message.answer("📭 Kanallar yo'q.", reply_markup=kb.admin_main_menu())
        return
    text = f"📡 <b>Majburiy kanallar</b> ({len(channels)} ta):\n\n"
    for i, (ch_id, ch_name, ch_link) in enumerate(channels, 1):
        text += f"{i}. <b>{ch_name}</b>\n   🔗 {ch_link}\n   🆔 <code>{ch_id}</code>\n\n"
    await message.answer(text, parse_mode="HTML", reply_markup=kb.admin_main_menu())

# --- STATISTIKA ---

@admin_router.message(F.text == "📊 Statistika")
async def statistics(message: Message):
    if not is_admin(message.from_user.id):
        return
    total_users = await db.get_users_count()
    today_users = await db.get_today_users_count()
    total_views = await db.get_total_views_count()
    today_views = await db.get_today_views_count()
    total_movies = await db.get_movies_count()
    today_pop = await db.get_today_popular_movies()
    all_pop = await db.get_all_popular_movies()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
        f"📅 Bugun faol: <b>{today_users}</b>\n\n"
        f"🎬 Jami kinolar: <b>{total_movies}</b>\n"
        f"👁 Jami ko'rishlar: <b>{total_views}</b>\n"
        f"📅 Bugun ko'rishlar: <b>{today_views}</b>"
    )
    if today_pop:
        text += "\n\n🔥 <b>Bugungi mashhur:</b>\n"
        for title, code, views in today_pop:
            text += f"   • <code>{code}</code> — {title}: <b>{views}</b>\n"
    if all_pop:
        text += "\n\n🏆 <b>Eng mashhur:</b>\n"
        for title, code, views in all_pop:
            text += f"   • <code>{code}</code> — {title}: <b>{views}</b>\n"
    await message.answer(text, parse_mode="HTML", reply_markup=kb.admin_main_menu())

# --- FOYDALANUVCHILAR ---

@admin_router.message(F.text == "👥 Foydalanuvchilar")
async def users_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = await db.get_all_users()
    count = await db.get_users_count()
    if not users:
        await message.answer("📭 Foydalanuvchilar yo'q.", reply_markup=kb.admin_main_menu())
        return
    text = f"👥 <b>Foydalanuvchilar</b> ({count} ta):\n\n"
    for uid, uname, fname, joined in users[:50]:
        un = f"@{uname}" if uname else "—"
        text += f"• <b>{fname}</b> ({un}) — <code>{uid}</code>\n"
    if count > 50:
        text += f"\n...va yana <b>{count-50}</b> ta"
    await message.answer(text, parse_mode="HTML", reply_markup=kb.admin_main_menu())

# --- BROADCAST ---

@admin_router.message(F.text == "📨 Hammaga xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    count = await db.get_users_count()
    await state.set_state(Broadcast.waiting_message)
    await message.answer(
        f"📨 <b>Ommaviy xabar</b>\n👥 {count} ta foydalanuvchi\n\nXabarni yuboring (matn/rasm/video/ovoz/audio/hujjat):",
        parse_mode="HTML", reply_markup=kb.cancel_keyboard()
    )

@admin_router.message(Broadcast.waiting_message)
async def broadcast_confirm(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text:
        msg_type, content = "text", message.text
    elif message.photo:
        msg_type, content = "photo", message.photo[-1].file_id
    elif message.video:
        msg_type, content = "video", message.video.file_id
    elif message.voice:
        msg_type, content = "voice", message.voice.file_id
    elif message.audio:
        msg_type, content = "audio", message.audio.file_id
    elif message.document:
        msg_type, content = "document", message.document.file_id
    else:
        await message.answer("❌ Noto'g'ri tur!")
        return
    caption = message.caption or ""
    await state.update_data(msg_type=msg_type, content=content, caption=caption)
    await state.set_state(Broadcast.confirm)
    count = await db.get_users_count()
    await message.answer(
        f"📨 <b>{count}</b> ta foydalanuvchiga yuboriladi. Tasdiqlaysizmi?",
        parse_mode="HTML", reply_markup=kb.confirm_keyboard()
    )

@admin_router.callback_query(F.data == "confirm_broadcast")
async def broadcast_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    msg_type = data.get("msg_type")
    content = data.get("content")
    caption = data.get("caption", "")
    await state.clear()
    await callback.message.delete()
    user_ids = await db.get_all_user_ids()
    total = len(user_ids)
    status_msg = await callback.message.answer(f"⏳ 0/{total}")
    success = failed = 0
    for i, uid in enumerate(user_ids):
        try:
            if msg_type == "text":
                await bot.send_message(uid, content, parse_mode="HTML")
            elif msg_type == "photo":
                await bot.send_photo(uid, content, caption=caption, parse_mode="HTML")
            elif msg_type == "video":
                await bot.send_video(uid, content, caption=caption, parse_mode="HTML")
            elif msg_type == "voice":
                await bot.send_voice(uid, content)
            elif msg_type == "audio":
                await bot.send_audio(uid, content, caption=caption, parse_mode="HTML")
            elif msg_type == "document":
                await bot.send_document(uid, content, caption=caption, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1
        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(f"⏳ {i+1}/{total}")
            except Exception:
                pass
        await asyncio.sleep(0.05)
    await status_msg.edit_text(
        f"✅ <b>Yakunlandi!</b>\n✅ Yuborildi: <b>{success}</b>\n❌ Xato: <b>{failed}</b>",
        parse_mode="HTML"
    )
    await callback.message.answer("Admin panel:", reply_markup=kb.admin_main_menu())
    await callback.answer()

@admin_router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Bekor qilindi.", reply_markup=kb.admin_main_menu())
    await callback.answer()

# ==================== USER HANDLERS ====================

@user_router.message(CommandStart(), StateFilter(default_state))
async def start_handler(message: Message, bot: Bot):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 <b>Admin, xush kelibsiz!</b>\n/admin — panel", parse_mode="HTML")
        return
    not_sub = await get_not_subscribed(bot, message.from_user.id)
    if not_sub:
        await send_sub_msg(message, not_sub)
        return
    await message.answer(
        f"🎬 <b>Kino Bot</b>ga xush kelibsiz, {message.from_user.first_name}!\n\n"
        "Kino kodini yuboring. Masalan: <code>1</code>",
        parse_mode="HTML"
    )

@user_router.callback_query(F.data == "check_subscription")
async def check_sub_callback(callback: CallbackQuery, bot: Bot):
    not_sub = await get_not_subscribed(bot, callback.from_user.id)
    if not_sub:
        names = ", ".join(ch[1] for ch in not_sub)
        await callback.answer(f"❌ Hali obuna bo'lmadingiz: {names}", show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=kb.subscription_keyboard(not_sub))
        except Exception:
            pass
        return
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        f"✅ <b>Obuna tasdiqlandi!</b>\n\n"
        f"🎬 Xush kelibsiz, {callback.from_user.first_name}!\n\nKino kodini yuboring:",
        parse_mode="HTML"
    )
    await callback.answer("✅ Tasdiqlandi!")

@user_router.message(F.text, StateFilter(default_state))
async def movie_code_handler(message: Message, bot: Bot):
    if message.from_user.id == ADMIN_ID:
        return
    not_sub = await get_not_subscribed(bot, message.from_user.id)
    if not_sub:
        await send_sub_msg(message, not_sub)
        return
    code = message.text.strip()
    movie = await db.get_movie_by_code(code)
    if not movie:
        await message.answer(f"❌ <b>{code}</b> kodli kino topilmadi.", parse_mode="HTML")
        return
    m_code, m_title, m_desc, m_file_id, m_file_type, m_thumbnail = movie
    await db.log_movie_view(message.from_user.id, m_code, m_title)
    caption = f"🎬 <b>{m_title}</b>"
    if m_desc:
        caption += f"\n\n📝 {m_desc}"
    caption += f"\n\n🔢 Kod: <code>{m_code}</code>"
    try:
        if m_file_type == "video":
            await message.answer_video(video=m_file_id, caption=caption, parse_mode="HTML")
        elif m_file_type == "document":
            await message.answer_document(document=m_file_id, caption=caption, parse_mode="HTML")
        elif m_file_type == "audio":
            await message.answer_audio(audio=m_file_id, caption=caption, parse_mode="HTML")
        elif m_file_type == "photo":
            await message.answer_photo(photo=m_file_id, caption=caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"⚠️ Xatolik: {str(e)[:100]}")

# ==================== MAIN ====================

async def main():
    logger.info("Ma'lumotlar bazasi ishga tushirilmoqda...")
    await db.init_db()
    logger.info("Tayyor!")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(UserRegisterMiddleware())
    dp.callback_query.middleware(UserRegisterMiddleware())

    dp.include_router(admin_router)
    dp.include_router(user_router)

    bot_info = await bot.get_me()
    logger.info(f"Bot: @{bot_info.username} | Admin: {ADMIN_ID}")

    try:
        await bot.set_my_commands(
            commands=[
                BotCommand(command="start", description="Botni ishga tushirish"),
                BotCommand(command="admin", description="Admin panel")
            ],
            scope=BotCommandScopeDefault()
        )
    except Exception as e:
        logger.error(f"Buyruqlarni o'rnatishda xatolik: {e}")

    try:
        await bot.send_message(ADMIN_ID, f"✅ <b>Bot ishga tushdi!</b>\n🤖 @{bot_info.username}")
    except Exception:
        pass

    logger.info("Polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
