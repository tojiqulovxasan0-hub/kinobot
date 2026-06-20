from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.state import default_state
import database as db
import keyboards as kb
from config import ADMIN_ID
import logging

router = Router()
logger = logging.getLogger(__name__)


async def get_not_subscribed_channels(bot: Bot, user_id: int) -> list:
    """
    Foydalanuvchi obuna bo'lmagan kanallar ro'yxatini qaytaradi.
    Bo'sh ro'yxat = barcha kanallarga obuna bo'lgan.
    """
    channels = await db.get_all_channels()

    # Majburiy kanal yo'q — ruxsat beriladi
    if not channels:
        return []

    not_subscribed = []
    for ch_id, ch_name, ch_link in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            # left, kicked, banned — obuna emas
            if member.status in ("left", "kicked", "banned"):
                not_subscribed.append((ch_id, ch_name, ch_link))
                logger.info(f"User {user_id} not subscribed to {ch_name} ({ch_id}), status: {member.status}")
            else:
                logger.info(f"User {user_id} subscribed to {ch_name} ({ch_id}), status: {member.status}")
        except Exception as e:
            # Kanal topilmasa yoki xatolik — obuna emas deb hisoblaymiz
            logger.warning(f"Error checking subscription for user {user_id} in {ch_id}: {e}")
            not_subscribed.append((ch_id, ch_name, ch_link))

    return not_subscribed


async def send_subscribe_message(message: Message, not_subscribed: list):
    """Obuna talab qiluvchi xabar yuborish"""
    count = len(not_subscribed)
    text = (
        f"⛔️ <b>Botdan foydalanish uchun {count} ta kanalga obuna bo'lishingiz kerak!</b>\n\n"
        "👇 Quyidagi kanallarga obuna bo'ling va ✅ <b>Tekshirish</b> tugmasini bosing:"
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb.subscription_keyboard(not_subscribed)
    )


# ==================== /start ====================

@router.message(CommandStart(), StateFilter(default_state))
async def start_handler(message: Message, bot: Bot):
    user = message.from_user

    # Admin uchun alohida
    if user.id == ADMIN_ID:
        await message.answer(
            "👑 <b>Admin, xush kelibsiz!</b>\n\n"
            "Admin panelni ochish uchun /admin buyrug'ini yuboring.",
            parse_mode="HTML"
        )
        return

    # Obuna tekshiruvi
    not_subscribed = await get_not_subscribed_channels(bot, user.id)
    if not_subscribed:
        await send_subscribe_message(message, not_subscribed)
        return

    await message.answer(
        f"🎬 <b>Kino Bot</b>ga xush kelibsiz, {user.first_name}!\n\n"
        "Kino olish uchun kino <b>kodini</b> yuboring.\n"
        "Masalan: <code>1</code> yoki <code>23</code>",
        parse_mode="HTML"
    )


# ==================== OBUNA TEKSHIRISH TUGMASI ====================

@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, bot: Bot):
    user = callback.from_user

    not_subscribed = await get_not_subscribed_channels(bot, user.id)

    if not_subscribed:
        # Hali obuna bo'lmagan kanallar bor
        names = ", ".join(ch[1] for ch in not_subscribed)
        await callback.answer(
            f"❌ Hali obuna bo'lmagan kanallar: {names}",
            show_alert=True
        )
        # Tugmalarni yangilaymiz (yangi not_subscribed ro'yxati bilan)
        try:
            await callback.message.edit_reply_markup(
                reply_markup=kb.subscription_keyboard(not_subscribed)
            )
        except Exception:
            pass
        return

    # Barcha kanallarga obuna bo'ldi
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"✅ <b>Obuna tasdiqlandi!</b>\n\n"
        f"🎬 Xush kelibsiz, {user.first_name}!\n\n"
        "Kino olish uchun kino <b>kodini</b> yuboring.\n"
        "Masalan: <code>1</code> yoki <code>23</code>",
        parse_mode="HTML"
    )
    await callback.answer("✅ Obuna tasdiqlandi!")


# ==================== KINO KODI ====================

@router.message(F.text, StateFilter(default_state))
async def movie_code_handler(message: Message, bot: Bot):
    user = message.from_user

    # Adminni o'tkazib yuboramiz
    if user.id == ADMIN_ID:
        return

    # Har safar obuna tekshiramiz — chiqib ketgan bo'lsa ham ushlaydi
    not_subscribed = await get_not_subscribed_channels(bot, user.id)
    if not_subscribed:
        await send_subscribe_message(message, not_subscribed)
        return

    code = message.text.strip()
    movie = await db.get_movie_by_code(code)

    if not movie:
        await message.answer(
            f"❌ <b>{code}</b> kodli kino topilmadi.\n\n"
            "Iltimos, to'g'ri kino kodini kiriting.",
            parse_mode="HTML"
        )
        return

    m_code, m_title, m_desc, m_file_id, m_file_type, m_thumbnail = movie

    # Ko'rishni log qilish
    await db.log_movie_view(user.id, m_code, m_title)

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
        err = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await message.answer(
            f"⚠️ Kinoni yuborishda xatolik yuz berdi.\nXato: {err}",
            parse_mode="HTML"
        )
