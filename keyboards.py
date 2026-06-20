from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


# ==================== ADMIN KEYBOARDS ====================

def admin_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Kino qo'shish"), KeyboardButton(text="🗑 Kino o'chirish")],
            [KeyboardButton(text="📋 Kinolar ro'yxati"), KeyboardButton(text="📢 Kanal qo'shish")],
            [KeyboardButton(text="❌ Kanal o'chirish"), KeyboardButton(text="📡 Kanallar ro'yxati")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Foydalanuvchilar")],
            [KeyboardButton(text="📨 Hammaga xabar yuborish")],
        ],
        resize_keyboard=True
    )
    return keyboard


def cancel_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )
    return keyboard


def confirm_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, yuborish", callback_data="confirm_broadcast"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_broadcast"),
        ]
    ])
    return keyboard


# ==================== USER KEYBOARDS ====================

def subscription_keyboard(channels: list):
    """Majburiy kanallar tugmalari"""
    buttons = []
    for ch_id, ch_name, ch_link in channels:
        buttons.append([InlineKeyboardButton(text=f"➕ {ch_name} ga obuna bo'lish", url=ch_link)])
    buttons.append([InlineKeyboardButton(text="✅ Obuna bo'ldim — Tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def movie_delete_keyboard(code: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🗑 Kinoni o'chirish (kod: {code})", callback_data=f"del_movie:{code}")]
    ])
