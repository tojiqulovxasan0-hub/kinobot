from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database as db
import keyboards as kb
import asyncio
from config import ADMIN_ID

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


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


# ==================== ADMIN PANEL ====================

@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "👑 <b>Admin Panel</b>\n\nQuyidagi amallardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=kb.admin_main_menu()
    )


# Bekor qilish — barcha holatlar uchun
@router.message(F.text == "❌ Bekor qilish", StateFilter("*"))
async def cancel_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("❌ Amal bekor qilindi.", reply_markup=kb.admin_main_menu())


# ==================== KINO QO'SHISH ====================

@router.message(F.text == "🎬 Kino qo'shish")
async def add_movie_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddMovie.waiting_code)
    await message.answer(
        "🔢 Kino kodini kiriting:\n"
        "(Masalan: <code>1</code>, <code>42</code>, <code>action1</code>)",
        parse_mode="HTML",
        reply_markup=kb.cancel_keyboard()
    )


@router.message(AddMovie.waiting_code, F.text)
async def add_movie_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    code = message.text.strip()

    if await db.movie_exists(code):
        await message.answer(
            f"⚠️ <b>{code}</b> kodli kino allaqachon mavjud! Boshqa kod kiriting.",
            parse_mode="HTML"
        )
        return

    await state.update_data(code=code)
    await state.set_state(AddMovie.waiting_file)
    await message.answer(
        "🎬 Endi kinoni yuboring:\n"
        "• Video fayl\n"
        "• Hujjat (document)\n"
        "• Audio\n"
        "• Rasm",
        reply_markup=kb.cancel_keyboard()
    )


@router.message(AddMovie.waiting_file, F.video | F.document | F.audio | F.photo)
async def add_movie_file(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    else:
        await message.answer("❌ Noto'g'ri fayl turi! Video, hujjat, audio yoki rasm yuboring.")
        return

    await state.update_data(file_id=file_id, file_type=file_type)
    await state.set_state(AddMovie.waiting_title)
    await message.answer(
        "✏️ Kino nomini kiriting:\n"
        "(Masalan: <code>Avatar 2</code>)",
        parse_mode="HTML",
        reply_markup=kb.cancel_keyboard()
    )


@router.message(AddMovie.waiting_title, F.text)
async def add_movie_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(AddMovie.waiting_description)
    await message.answer(
        "📝 Kino tavsifini kiriting:\n"
        "(Yoki <code>-</code> kiriting agar tavsif kerak bo'lmasa)",
        parse_mode="HTML",
        reply_markup=kb.cancel_keyboard()
    )


@router.message(AddMovie.waiting_description, F.text)
async def add_movie_description(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    description = message.text.strip()
    if description == "-":
        description = None

    data = await state.get_data()
    code = data["code"]
    file_id = data["file_id"]
    file_type = data["file_type"]
    title = data["title"]

    try:
        await db.add_movie(
            code=code,
            title=title,
            description=description,
            file_id=file_id,
            file_type=file_type
        )
        await state.clear()
        await message.answer(
            f"✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
            f"🔢 Kod: <code>{code}</code>\n"
            f"🎬 Nomi: <b>{title}</b>\n"
            f"📁 Turi: {file_type}\n"
            f"📝 Tavsif: {description or 'Yo\'q'}",
            parse_mode="HTML",
            reply_markup=kb.admin_main_menu()
        )
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Kinoni saqlashda xatolik: <code>{e}</code>",
            parse_mode="HTML",
            reply_markup=kb.admin_main_menu()
        )


# ==================== KINO O'CHIRISH ====================

@router.message(F.text == "🗑 Kino o'chirish")
async def delete_movie_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(DeleteMovie.waiting_code)
    await message.answer(
        "🔢 O'chirmoqchi bo'lgan kino kodini kiriting:",
        reply_markup=kb.cancel_keyboard()
    )


@router.message(DeleteMovie.waiting_code, F.text)
async def delete_movie_by_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    code = message.text.strip()
    movie = await db.get_movie_by_code(code)

    if not movie:
        await message.answer(
            f"❌ <b>{code}</b> kodli kino topilmadi!\n\nBoshqa kod kiriting yoki bekor qiling.",
            parse_mode="HTML"
        )
        return

    await db.delete_movie(code)
    await state.clear()
    await message.answer(
        f"✅ <b>{movie[1]}</b> (kod: <code>{code}</code>) kinosi o'chirildi!",
        parse_mode="HTML",
        reply_markup=kb.admin_main_menu()
    )


# ==================== KINOLAR RO'YXATI ====================

@router.message(F.text == "📋 Kinolar ro'yxati")
async def movies_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    movies = await db.get_all_movies()
    if not movies:
        await message.answer("📭 Hozircha kinolar yo'q.", reply_markup=kb.admin_main_menu())
        return

    text = f"🎬 <b>Kinolar ro'yxati</b> ({len(movies)} ta):\n\n"
    chunk = ""
    for i, (code, title, desc, file_id, file_type, added_at) in enumerate(movies, 1):
        line = f"{i}. <code>{code}</code> — <b>{title}</b> ({file_type})\n"
        if len(chunk) + len(line) > 3500:
            await message.answer(text + chunk, parse_mode="HTML")
            chunk = line
        else:
            chunk += line

    if chunk:
        await message.answer(text + chunk if text != f"🎬 <b>Kinolar ro'yxati</b> ({len(movies)} ta):\n\n" else chunk,
                             parse_mode="HTML", reply_markup=kb.admin_main_menu())


# ==================== KANAL QO'SHISH ====================

@router.message(F.text == "📢 Kanal qo'shish")
async def add_channel_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddChannel.waiting_channel_id)
    await message.answer(
        "📢 <b>Kanal qo'shish</b>\n\n"
        "Kanal ID sini yuboring:\n"
        "Misol: <code>-1001234567890</code>\n\n"
        "📌 Kanal ID ni bilish uchun:\n"
        "1. Kanalga @username_to_id_bot ni qo'shing\n"
        "2. Yoki kanalga forward qilib @userinfobot ga yuboring\n\n"
        "⚠️ <b>Muhim:</b> Bot kanalga <b>admin</b> bo'lishi shart!",
        parse_mode="HTML",
        reply_markup=kb.cancel_keyboard()
    )


@router.message(AddChannel.waiting_channel_id, F.text)
async def add_channel_process(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    raw = message.text.strip()

    # Faqat raqam va minus belgisi qabul qilinadi
    if not raw.lstrip('-').isdigit():
        await message.answer(
            "❌ Noto'g'ri format!\n\n"
            "Kanal ID faqat raqamlardan iborat bo'lishi kerak.\n"
            "Misol: <code>-1001234567890</code>",
            parse_mode="HTML"
        )
        return

    channel_id = raw

    # Bot admin ekanligini tekshirish — get_chat ishlatmaymiz (aiogram bug)
    # Faqat get_chat_member ishlatamiz
    channel_name = None
    channel_link = None

    try:
        bot_me = await bot.get_me()
        bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot_me.id)
        if bot_member.status not in ("administrator", "creator"):
            await message.answer(
                "❌ Bot kanalda <b>admin emas</b>!\n\n"
                "1. Kanalga kiring\n"
                "2. Botni admin qilib tayinlang\n"
                "3. Qayta urinib ko'ring",
                parse_mode="HTML"
            )
            return
        # get_chat_member dan chat nomini olamiz
        if hasattr(bot_member, 'chat') and bot_member.chat:
            channel_name = getattr(bot_member.chat, 'title', None)
    except Exception as e:
        err = str(e).replace('<', '').replace('>', '')
        await message.answer(
            f"❌ Kanal topilmadi yoki bot admin emas!\n\n"
            f"Sabab: {err}\n\n"
            "Tekshiring:\n"
            "• Kanal ID to'g'ri kiritilganmi\n"
            "• Bot kanalga admin qilib qo'shilganmi",
            parse_mode="HTML"
        )
        return

    # Kanal nomini Telegram API orqali xavfsiz olish
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{bot.token}/getChat"
            async with session.post(url, json={"chat_id": channel_id}) as resp:
                data = await resp.json()
                if data.get("ok"):
                    result = data["result"]
                    channel_name = result.get("title", channel_name or "Kanal")
                    username = result.get("username")
                    invite = result.get("invite_link")
                    if username:
                        channel_link = f"https://t.me/{username}"
                    elif invite:
                        channel_link = invite
    except Exception:
        pass

    # Agar hali ham link yo'q bo'lsa — invite link yaratamiz
    if not channel_link:
        try:
            inv = await bot.create_chat_invite_link(chat_id=channel_id)
            channel_link = inv.invite_link
        except Exception:
            numeric_id = str(channel_id).replace("-100", "")
            channel_link = f"https://t.me/c/{numeric_id}"

    if not channel_name:
        channel_name = f"Kanal {channel_id}"

    # Bazaga qo'shish
    try:
        await db.add_channel(channel_id, channel_name, channel_link)
    except Exception as e:
        err = str(e).replace('<', '').replace('>', '')
        await state.clear()
        await message.answer(
            f"❌ Kanalni saqlashda xatolik: {err}",
            reply_markup=kb.admin_main_menu()
        )
        return

    await state.clear()
    await message.answer(
        f"✅ <b>{channel_name}</b> kanali muvaffaqiyatli qo'shildi!\n\n"
        f"🆔 ID: <code>{channel_id}</code>\n"
        f"🔗 Link: {channel_link}",
        parse_mode="HTML",
        reply_markup=kb.admin_main_menu()
    )


# ==================== KANAL O'CHIRISH ====================

@router.message(F.text == "❌ Kanal o'chirish")
async def remove_channel_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    channels = await db.get_all_channels()
    if not channels:
        await message.answer("📭 Hozircha majburiy kanallar yo'q.", reply_markup=kb.admin_main_menu())
        return

    text = "📡 <b>Mavjud kanallar:</b>\n\n"
    for i, (ch_id, ch_name, ch_link) in enumerate(channels, 1):
        text += f"{i}. <b>{ch_name}</b>\n   🆔 <code>{ch_id}</code>\n\n"
    text += "O'chirmoqchi bo'lgan kanal <b>ID</b> sini kiriting:"

    await state.set_state(RemoveChannel.waiting_channel_id)
    await message.answer(text, parse_mode="HTML", reply_markup=kb.cancel_keyboard())


@router.message(RemoveChannel.waiting_channel_id, F.text)
async def remove_channel_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    channel_id = message.text.strip()

    # Mavjudligini tekshirish
    channels = await db.get_all_channels()
    ch_ids = [ch[0] for ch in channels]

    if channel_id not in ch_ids:
        await message.answer(
            f"❌ <code>{channel_id}</code> ID li kanal ro'yxatda topilmadi!\n\n"
            "Yuqoridagi ro'yxatdan to'g'ri ID ni kiriting.",
            parse_mode="HTML"
        )
        return

    await db.remove_channel(channel_id)
    await state.clear()
    await message.answer(
        f"✅ <code>{channel_id}</code> kanali ro'yxatdan o'chirildi!",
        parse_mode="HTML",
        reply_markup=kb.admin_main_menu()
    )


# ==================== KANALLAR RO'YXATI ====================

@router.message(F.text == "📡 Kanallar ro'yxati")
async def channels_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    channels = await db.get_all_channels()
    if not channels:
        await message.answer("📭 Hozircha majburiy kanallar yo'q.", reply_markup=kb.admin_main_menu())
        return

    text = f"📡 <b>Majburiy kanallar</b> ({len(channels)} ta):\n\n"
    for i, (ch_id, ch_name, ch_link) in enumerate(channels, 1):
        text += f"{i}. <b>{ch_name}</b>\n   🔗 {ch_link}\n   🆔 <code>{ch_id}</code>\n\n"

    await message.answer(text, parse_mode="HTML", reply_markup=kb.admin_main_menu())


# ==================== STATISTIKA ====================

@router.message(F.text == "📊 Statistika")
async def statistics(message: Message):
    if not is_admin(message.from_user.id):
        return

    total_users = await db.get_users_count()
    today_users = await db.get_today_users_count()
    total_views = await db.get_total_views_count()
    today_views = await db.get_today_views_count()
    total_movies = await db.get_movies_count()
    today_popular = await db.get_today_popular_movies()
    all_popular = await db.get_all_popular_movies()

    text = (
        "📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
        f"📅 Bugun faol: <b>{today_users}</b>\n\n"
        f"🎬 Jami kinolar: <b>{total_movies}</b>\n"
        f"👁 Jami ko'rishlar: <b>{total_views}</b>\n"
        f"📅 Bugun ko'rishlar: <b>{today_views}</b>"
    )

    if today_popular:
        text += "\n\n🔥 <b>Bugungi mashhur kinolar:</b>\n"
        for title, code, views in today_popular:
            text += f"  • <code>{code}</code> — {title}: <b>{views}</b> marta\n"

    if all_popular:
        text += "\n\n🏆 <b>Eng mashhur kinolar:</b>\n"
        for title, code, views in all_popular:
            text += f"  • <code>{code}</code> — {title}: <b>{views}</b> marta\n"

    await message.answer(text, parse_mode="HTML", reply_markup=kb.admin_main_menu())


# ==================== FOYDALANUVCHILAR ====================

@router.message(F.text == "👥 Foydalanuvchilar")
async def users_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    users = await db.get_all_users()
    count = await db.get_users_count()

    if not users:
        await message.answer("📭 Hozircha foydalanuvchilar yo'q.", reply_markup=kb.admin_main_menu())
        return

    text = f"👥 <b>Foydalanuvchilar ro'yxati</b> ({count} ta):\n\n"
    for user_id, username, full_name, joined_at in users[:50]:
        uname = f"@{username}" if username else "—"
        text += f"• <b>{full_name}</b> ({uname})\n  🆔 <code>{user_id}</code> | 📅 {joined_at[:10]}\n\n"

    if count > 50:
        text += f"...va yana <b>{count - 50}</b> ta foydalanuvchi"

    await message.answer(text, parse_mode="HTML", reply_markup=kb.admin_main_menu())


# ==================== HAMMAGA XABAR YUBORISH ====================

@router.message(F.text == "📨 Hammaga xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    users_count = await db.get_users_count()
    await state.set_state(Broadcast.waiting_message)
    await message.answer(
        f"📨 <b>Ommaviy xabar yuborish</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{users_count}</b>\n\n"
        "Yuboriladigan xabarni yuboring:\n"
        "• Matn\n"
        "• Rasm (caption bilan)\n"
        "• Video (caption bilan)\n"
        "• Ovozli xabar\n"
        "• Audio\n"
        "• Hujjat",
        parse_mode="HTML",
        reply_markup=kb.cancel_keyboard()
    )


@router.message(Broadcast.waiting_message)
async def broadcast_confirm(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text:
        msg_type = "text"
        content = message.text
    elif message.photo:
        msg_type = "photo"
        content = message.photo[-1].file_id
    elif message.video:
        msg_type = "video"
        content = message.video.file_id
    elif message.voice:
        msg_type = "voice"
        content = message.voice.file_id
    elif message.audio:
        msg_type = "audio"
        content = message.audio.file_id
    elif message.document:
        msg_type = "document"
        content = message.document.file_id
    else:
        await message.answer("❌ Noto'g'ri xabar turi! Matn, rasm, video, ovoz, audio yoki hujjat yuboring.")
        return

    caption = message.caption or ""
    await state.update_data(msg_type=msg_type, content=content, caption=caption)
    await state.set_state(Broadcast.confirm)

    users_count = await db.get_users_count()
    await message.answer(
        f"📨 <b>Xabarni tasdiqlang</b>\n\n"
        f"Tur: <b>{msg_type}</b>\n"
        f"Xabar <b>{users_count}</b> ta foydalanuvchiga yuboriladi.\n\n"
        "Davom etasizmi?",
        parse_mode="HTML",
        reply_markup=kb.confirm_keyboard()
    )


@router.callback_query(F.data == "confirm_broadcast")
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

    if total == 0:
        await callback.message.answer("📭 Foydalanuvchilar yo'q.", reply_markup=kb.admin_main_menu())
        await callback.answer()
        return

    status_msg = await callback.message.answer(f"⏳ Xabar yuborilmoqda... 0/{total}")

    success = 0
    failed = 0

    for i, uid in enumerate(user_ids):
        try:
            if msg_type == "text":
                await bot.send_message(uid, content, parse_mode="HTML")
            elif msg_type == "photo":
                await bot.send_photo(uid, content, caption=caption, parse_mode="HTML")
            elif msg_type == "video":
                await bot.send_video(uid, content, caption=caption, parse_mode="HTML")
            elif msg_type == "voice":
                await bot.send_voice(uid, content, caption=caption)
            elif msg_type == "audio":
                await bot.send_audio(uid, content, caption=caption, parse_mode="HTML")
            elif msg_type == "document":
                await bot.send_document(uid, content, caption=caption, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1

        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(f"⏳ Xabar yuborilmoqda... {i + 1}/{total}")
            except Exception:
                pass

        await asyncio.sleep(0.05)

    try:
        await status_msg.edit_text(
            f"✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
            f"✅ Muvaffaqiyatli: <b>{success}</b>\n"
            f"❌ Xato (bot bloklangan): <b>{failed}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.answer("Admin panel:", reply_markup=kb.admin_main_menu())
    await callback.answer()


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Xabar yuborish bekor qilindi.", reply_markup=kb.admin_main_menu())
    await callback.answer()
